import { CalendarClock, CheckCircle2, FileText, Loader2, Zap, X } from "lucide-react";

import { API_BASE_URL, platformStyles } from "../constants";
import { publishTypeForPost } from "../utils";

const accountLabelForPost = (post) =>
  post.accountLabel ||
  (post.account
    ? post.account
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")
    : "Default account");

function PostItem({ post }) {
  const publishType = publishTypeForPost(post);

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
          <span className={`publish-type-badge ${publishType}`}>
            {publishType === "scheduled" ? <CalendarClock size={13} /> : <Zap size={13} />}
            {publishType === "scheduled" ? "Scheduled" : "Instant"}
          </span>
          <span className="account-badge">{accountLabelForPost(post)}</span>
          <time>{new Date(post.createdAt).toLocaleString()}</time>
          {post.status === "scheduled" && post.scheduledAt && (
            <time>Scheduled: {new Date(post.scheduledAt).toLocaleString()}</time>
          )}
        </div>
      </div>

      <div className="result-row">
        {post.results.map((result) => (
          <span
            className={`result-pill ${result.status}`}
            key={result.platform}
            title={result.message}
          >
            {result.status === "scheduled" ? (
              <CalendarClock size={14} />
            ) : result.status === "publishing" ? (
              <Loader2 className="spin" size={14} />
            ) : ["dry_run", "published"].includes(result.status) ? (
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
