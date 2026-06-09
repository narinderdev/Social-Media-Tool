import { CheckCircle2, FileText, X } from "lucide-react";

import { API_BASE_URL, platformStyles } from "../constants";

function PostItem({ post }) {
  return (
    <article className="post-item">
      <div className="post-summary">
        {post.media ? (
          post.media.mimeType.startsWith("video/") ? (
            <video src={`${API_BASE_URL}${post.media.url}`} muted />
          ) : (
            <img src={`${API_BASE_URL}${post.media.url}`} alt="" />
          )
        ) : (
          <div className="text-tile">
            <FileText size={22} />
          </div>
        )}
        <div>
          <p>{post.caption || "Media post without caption"}</p>
          <time>{new Date(post.createdAt).toLocaleString()}</time>
        </div>
      </div>

      <div className="result-row">
        {post.results.map((result) => (
          <span
            className={`result-pill ${result.status}`}
            key={result.platform}
            title={result.message}
          >
            {["dry_run", "published"].includes(result.status) ? (
              <CheckCircle2 size={14} />
            ) : (
              <X size={14} />
            )}
            {platformStyles[result.platform]?.name || result.platform}
          </span>
        ))}
      </div>
    </article>
  );
}

export default PostItem;
