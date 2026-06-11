import { renderMarkdown } from "../lib/markdown.js";
import FlowRail from "./FlowRail.jsx";

export default function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={"msg " + (isUser ? "user" : "agent")}>
      <span className="msg-role">{isUser ? "you" : "zero-to-synced"}</span>

      {/* live tool activity shows above the text while the turn is streaming */}
      {!isUser && msg.streaming && msg.tool && <FlowRail tool={msg.tool} />}

      {msg.text ? (
        <div className={"bubble" + (msg.error ? " error" : "")}>
          {isUser ? (
            <span style={{ whiteSpace: "pre-wrap" }}>{msg.text}</span>
          ) : (
            <div
              className="md"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
            />
          )}
        </div>
      ) : (
        !isUser &&
        msg.streaming &&
        !msg.tool && (
          <div className="bubble">
            <span className="typing">
              <i /><i /><i />
            </span>
          </div>
        )
      )}
    </div>
  );
}
