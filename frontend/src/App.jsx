import { useEffect, useRef, useState, useCallback } from "react";
import { api, auth, fivetran, token, setUnauthorizedHandler, sendMessage, uploadFile } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Message from "./components/Message.jsx";
import Composer from "./components/Composer.jsx";
import FileStrip from "./components/FileStrip.jsx";
import AuthScreen from "./components/AuthScreen.jsx";
import ConnectFivetran from "./components/ConnectFivetran.jsx";

const uid = () =>
  (crypto.randomUUID && crypto.randomUUID()) || Math.random().toString(36).slice(2);

const SUGGESTIONS = [
  "Sync my Shopify orders into BigQuery",
  "Combine Stripe revenue with my Postgres users table",
  "What connectors do I already have set up?",
];

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [ftConnected, setFtConnected] = useState(null); // null=unknown
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState(null);

  const streamRef = useRef(null);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions());
    } catch (e) {
      setBanner("Couldn't reach the backend. Is the API running on :8000?");
    }
  }, []);

  // Validate any stored token on load; log out automatically on 401 anywhere.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setFtConnected(null);
      setSessions([]);
      setMessages([]);
      setFiles([]);
      setActiveId(null);
    });

    (async () => {
      if (!token.get()) {
        setAuthChecking(false);
        return;
      }
      try {
        const me = await auth.me();
        setUser(me);
      } catch {
        token.clear();
      } finally {
        setAuthChecking(false);
      }
    })();
  }, []);

  // Once authenticated: check Fivetran connection and load sessions.
  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const { connected } = await fivetran.status();
        setFtConnected(connected);
      } catch {
        setFtConnected(false);
      }
    })();
    loadSessions();
  }, [user, loadSessions]);

  function logout() {
    token.clear();
    setUser(null);
    setFtConnected(null);
    setSessions([]);
    setMessages([]);
    setFiles([]);
    setActiveId(null);
    setInput("");
  }

  async function disconnectFivetran() {
    try {
      await fivetran.disconnect();
    } catch {
      /* ignore */
    }
    setFtConnected(false);
    setActiveId(null);
    setMessages([]);
    setFiles([]);
  }

  // auto-scroll to the newest message
  useEffect(() => {
    const el = streamRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function selectSession(sid) {
    setActiveId(sid);
    setMessages([]);
    setFiles([]);
    setBanner(null);
    try {
      const [hist, fileList] = await Promise.all([
        api.history(sid),
        api.listFiles(sid),
      ]);
      setMessages(
        hist.map((m) => ({ id: uid(), role: m.role, text: m.text }))
      );
      setFiles(fileList);
    } catch (e) {
      setBanner(`Couldn't load this session: ${e.message}`);
    }
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setFiles([]);
    setInput("");
    setBanner(null);
  }

  async function ensureSession(firstMessage) {
    if (activeId) return activeId;
    const { session_id } = await api.createSession();
    setActiveId(session_id);
    setSessions((s) => [
      {
        session_id,
        title: firstMessage?.slice(0, 48) || "New chat",
        created_at: new Date().toISOString(),
        last_active: new Date().toISOString(),
      },
      ...s,
    ]);
    return session_id;
  }

  function upsertFile(list, data) {
    const idx = list.findIndex((f) => f.file_id === data.file_id);
    const entry = {
      file_id: data.file_id,
      filename: data.filename,
      status: data.status,
      row_count: data.row_count,
      columns: data.columns,
    };
    if (idx === -1) return [entry, ...list];
    const copy = [...list];
    copy[idx] = entry;
    return copy;
  }

  // Shared streaming turn: creates an agent placeholder and applies SSE events.
  async function streamTurn(invoke) {
    const agentId = uid();
    setMessages((m) => [
      ...m,
      { id: agentId, role: "agent", text: "", streaming: true, tool: null },
    ]);
    setBusy(true);

    const patch = (fn) =>
      setMessages((m) => m.map((x) => (x.id === agentId ? fn(x) : x)));

    const onEvent = ({ event, data }) => {
      if (event === "token") {
        patch((x) => ({ ...x, text: x.text + (data.text || "") }));
      } else if (event === "tool") {
        patch((x) => ({ ...x, tool: { name: data.name, status: data.status } }));
      } else if (event === "file") {
        setFiles((f) => upsertFile(f, data));
      } else if (event === "done") {
        patch((x) => ({
          ...x,
          text: data.text && data.text.length ? data.text : x.text,
          streaming: false,
          tool: null,
        }));
      } else if (event === "error") {
        patch((x) => ({
          ...x,
          text: data.message || "Something went wrong.",
          error: true,
          streaming: false,
          tool: null,
        }));
      }
    };

    try {
      await invoke(onEvent);
    } catch (e) {
      patch((x) => ({
        ...x,
        text: x.text || `Connection error: ${e.message}`,
        error: !x.text,
        streaming: false,
        tool: null,
      }));
    } finally {
      setBusy(false);
      loadSessions();
    }
  }

  async function sendText(text) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBanner(null);
    let sid;
    try {
      sid = await ensureSession(trimmed);
    } catch (e) {
      setBanner(`Couldn't start a session: ${e.message}`);
      return;
    }
    setMessages((m) => [...m, { id: uid(), role: "user", text: trimmed }]);
    setInput("");
    await streamTurn((onEvent) => sendMessage(sid, trimmed, { onEvent }));
  }

  async function uploadAndStream(file) {
    if (busy) return;
    setBanner(null);
    let sid;
    try {
      sid = await ensureSession(`Uploaded ${file.name}`);
    } catch (e) {
      setBanner(`Couldn't start a session: ${e.message}`);
      return;
    }
    setMessages((m) => [
      ...m,
      { id: uid(), role: "user", text: `Uploaded ${file.name}` },
    ]);
    await streamTurn((onEvent) => uploadFile(sid, file, { onEvent }));
    try {
      setFiles(await api.listFiles(sid)); // reconcile final status
    } catch {
      /* non-fatal */
    }
  }

  const activeSession = sessions.find((s) => s.session_id === activeId);
  const firstUserMsg = messages.find((m) => m.role === "user")?.text;
  const headerTitle =
    (firstUserMsg && firstUserMsg.slice(0, 60)) ||
    activeSession?.title ||
    "New chat";
  const showEmpty = !activeId && messages.length === 0;

  if (authChecking) {
    return (
      <div className="boot">
        <div className="brand-mark" />
      </div>
    );
  }

  if (!user) {
    return <AuthScreen onAuthed={(u) => setUser(u)} />;
  }

  if (ftConnected === null) {
    return (
      <div className="boot">
        <div className="brand-mark" />
      </div>
    );
  }

  if (!ftConnected) {
    return (
      <ConnectFivetran
        userEmail={user.email}
        onConnected={() => setFtConnected(true)}
        onLogout={logout}
      />
    );
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={selectSession}
        onNew={newChat}
        user={user}
        onLogout={logout}
        onDisconnectFivetran={disconnectFivetran}
      />

      <main className="workspace">
        <header className="ws-header">
          <span className="ws-title">{headerTitle}</span>
          <span className="status-dot">
            <i /> live
          </span>
        </header>

        <FileStrip files={files} />

        {banner && <div className="banner">{banner}</div>}

        {showEmpty ? (
          <div className="empty">
            <h1>Turn plain English into a live data pipeline.</h1>
            <p>
              Tell me what data you want to bring together. I'll find the right
              Fivetran connectors, show you the plan, and only set things up once
              you say go.
            </p>
            <div className="suggest">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => sendText(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="stream" ref={streamRef}>
            <div className="stream-inner">
              {messages.map((m) => (
                <Message key={m.id} msg={m} />
              ))}
            </div>
          </div>
        )}

        <Composer
          value={input}
          onChange={setInput}
          onSend={() => sendText(input)}
          onUpload={uploadAndStream}
          busy={busy}
        />
      </main>
    </div>
  );
}
