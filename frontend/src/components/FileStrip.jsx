import { SheetIcon } from "./Icons.jsx";

export default function FileStrip({ files }) {
  if (!files.length) return null;
  return (
    <div className="file-strip">
      {files.map((f) => {
        const live = f.status === "uploaded_to_s3";
        return (
          <div className="file-chip" key={f.file_id}>
            <SheetIcon />
            <div>
              <div className="fc-name">{f.filename}</div>
              <div className="fc-meta">
                {f.row_count != null ? `${f.row_count.toLocaleString()} rows` : "—"}
                {f.columns ? ` · ${f.columns.length} cols` : ""}
              </div>
            </div>
            <span className={"fc-badge " + (live ? "live" : "ctx")}>
              {live ? "ready to sync" : "context"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
