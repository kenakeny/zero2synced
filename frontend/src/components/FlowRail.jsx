// The signature element: the agent's real tool activity rendered as a live
// connection to Fivetran. `tool` is the most recent { name, status } event.
export default function FlowRail({ tool }) {
  const active = tool?.status === "running";
  const label = tool?.name ? prettyTool(tool.name) : null;
  return (
    <div className="flow" aria-live="polite">
      <span className="flow-node">
        <span className="nd" /> agent
      </span>
      <span className={"flow-rail" + (active ? " active" : "")} />
      <span className="flow-node fivetran">
        <span className="nd" /> fivetran
      </span>
      {label && (
        <span className="flow-tool">
          <b>{label}</b>
          {active ? "…" : " ✓"}
        </span>
      )}
    </div>
  );
}

function prettyTool(name) {
  return String(name).replace(/_/g, " ");
}
