import { useRef } from "react";
import { SendIcon, ClipIcon } from "./Icons.jsx";

export default function Composer({ value, onChange, onSend, onUpload, busy }) {
  const fileRef = useRef(null);
  const taRef = useRef(null);

  const grow = (el) => {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!busy && value.trim()) onSend();
    }
  };

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    if (f) onUpload(f);
    e.target.value = ""; // allow re-uploading the same file
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          hidden
          onChange={pickFile}
        />
        <button
          className="icon-btn"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          title="Upload CSV or Excel"
          aria-label="Upload CSV or Excel"
        >
          <ClipIcon />
        </button>

        <textarea
          ref={taRef}
          rows={1}
          placeholder="Describe the data you want to sync…"
          value={value}
          disabled={busy}
          onChange={(e) => {
            onChange(e.target.value);
            grow(e.target);
          }}
          onKeyDown={handleKey}
        />

        <button
          className="send-btn"
          onClick={onSend}
          disabled={busy || !value.trim()}
          aria-label="Send message"
        >
          <SendIcon />
        </button>
      </div>
      <div className="composer-hint">
        <b>Enter</b> to send · <b>Shift+Enter</b> for a new line · attach a CSV/Excel to bring it in
      </div>
    </div>
  );
}
