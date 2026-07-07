import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  CalendarClock,
  CheckCircle2,
  FileText,
  Loader2,
  RefreshCw,
  Zap,
  X
} from "lucide-react";

import { API_BASE_URL, platformStyles } from "../constants";
import { apiFetch } from "../api";
import { publishTypeForPost } from "../utils";

const accountLabelForPost = (post) =>
  post.accountLabel ||
  (post.account
    ? post.account
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")
    : "Default account");

const successfulStatuses = new Set(["dry_run", "published", "scheduled", "publishing"]);

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "Not available";
  }

  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

const remoteStatusLabels = {
  available: "Published",
  missing: "Possibly deleted",
  unknown: "Unknown"
};

const formatStatus = (status) =>
  status
    ? status
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")
    : "Unknown";

const remoteStatusForMetric = (metric) => {
  if (!metric) {
    return "unknown";
  }
  if (metric.remoteStatus) {
    return metric.remoteStatus;
  }
  return metric.status === "missing" ? "missing" : "unknown";
};

const formatRemoteStatus = (status) => remoteStatusLabels[status] || formatStatus(status);

const formatPlatformMessage = (message) => {
  if (!message) {
    return "No message saved.";
  }

  const normalizedMessage = message.toLowerCase();
  if (
    normalizedMessage.includes("unsupported get request") ||
    normalizedMessage.includes("does not exist") ||
    normalizedMessage.includes("missing or inaccessible")
  ) {
    return (
      "Possibly deleted: the platform could not load this post ID, or the connected account "
      + "cannot read it."
    );
  }

  if (message.length > 180) {
    return `${message.slice(0, 177).trim()}...`;
  }

  return message;
};

const metricLabels = [
  ["impressions", "Impressions", "Times the post/media was shown."],
  ["views", "Views", "Media plays or media views reported by the platform."],
  ["reach", "Reach", "Unique accounts that saw it."],
  ["engagements", "Engagements", "Likes + comments + shares + clicks when no platform total exists."],
  ["likes", "Likes", "Reactions or likes on the post."],
  ["comments", "Comments", "Replies or comments on the post."],
  ["shares", "Shares", "Shares, reposts, or shared posts."],
  ["clicks", "Clicks", "Post, link, or profile clicks."],
  ["saves", "Saves", "Saves or bookmarks reported by the platform."]
];

const isMetricUnavailable = (platformMetric, metricKey) =>
  (platformMetric?.unavailableMetrics || []).includes(metricKey);

const formatMetricValue = (value, unavailable = false) => {
  if (unavailable) {
    return "N/A";
  }

  return Number.isFinite(value) ? new Intl.NumberFormat().format(value) : "0";
};

const aggregateMetric = (platformMetrics, metricKey) => {
  const metrics = Object.values(platformMetrics);
  const availableMetrics = metrics.filter(
    (platformMetric) => !isMetricUnavailable(platformMetric, metricKey)
  );

  if (metrics.length > 0 && availableMetrics.length === 0) {
    return { unavailable: true, value: null };
  }

  return {
    unavailable: false,
    value: availableMetrics.reduce((total, platformMetric) => {
      const value = platformMetric?.values?.[metricKey];
      return total + (Number.isFinite(value) ? value : 0);
    }, 0)
  };
};

const platformKeysForPost = (post) => [
  ...new Set([
    ...(post.results || []).map((result) => result.platform),
    ...(post.platforms || [])
  ])
];

const ResultIcon = ({ status, size = 14 }) =>
  status === "scheduled" ? (
    <CalendarClock size={size} />
  ) : status === "publishing" ? (
    <Loader2 className="spin" size={size} />
  ) : successfulStatuses.has(status) ? (
    <CheckCircle2 size={size} />
  ) : (
    <X size={size} />
  );

function PostStatsModal({ post, publishType, onClose }) {
  const [livePost, setLivePost] = useState(post);
  const [detailPlatform, setDetailPlatform] = useState("all");
  const [refreshState, setRefreshState] = useState("Manual refresh only");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshInFlight = useRef(false);
  const results = livePost.results || [];
  const mediaIsVideo = livePost.media?.mimeType?.startsWith("video/");
  const mediaType = livePost.media ? (mediaIsVideo ? "Video" : "Photo") : "Caption";
  const caption = livePost.caption?.trim() || "Media post without caption";
  const captionWordCount = useMemo(
    () => (livePost.caption?.trim() ? livePost.caption.trim().split(/\s+/).length : 0),
    [livePost.caption]
  );
  const successfulCount = results.filter((result) => successfulStatuses.has(result.status)).length;
  const platformMetrics = livePost.metrics?.platforms || {};
  const refreshedAt = livePost.metrics?.updatedAt
    ? new Date(livePost.metrics.updatedAt).toLocaleString()
    : "Not fetched yet";
  const availablePlatforms = useMemo(() => platformKeysForPost(livePost), [livePost]);
  const availablePlatformKey = availablePlatforms.join("|");
  const visibleResults =
    detailPlatform === "all"
      ? results
      : results.filter((result) => result.platform === detailPlatform);
  const visiblePlatformMetrics = useMemo(
    () =>
      Object.fromEntries(
        availablePlatforms
          .map((platform) => [platform, platformMetrics[platform]])
          .filter(([, metric]) => Boolean(metric))
      ),
    [availablePlatforms, platformMetrics]
  );

  const refreshMetrics = useCallback(async () => {
    const platforms = availablePlatformKey ? availablePlatformKey.split("|") : [];
    if (refreshInFlight.current || platforms.length === 0) {
      return;
    }

    refreshInFlight.current = true;
    setIsRefreshing(true);
    setRefreshState("Refreshing stats");

    try {
      const response = await apiFetch(`/api/posts/${livePost.id}/metrics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platforms })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Could not refresh stats.");
      }
      setLivePost(data.post);
      setRefreshState("Stats refreshed");
    } catch (error) {
      setRefreshState(error.message || "Refresh failed");
    } finally {
      refreshInFlight.current = false;
      setIsRefreshing(false);
    }
  }, [availablePlatformKey, livePost.id]);

  useEffect(() => {
    setLivePost(post);
    setDetailPlatform("all");
    setRefreshState("Manual refresh only");
  }, [post]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="post-stats-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`stats-title-${livePost.id}`}
      >
        <header className="stats-modal-header">
          <div>
            <p className="eyebrow">Stats</p>
            <h2 id={`stats-title-${livePost.id}`}>{mediaType} performance</h2>
          </div>
          <button
            className="icon-button stats-close-button"
            type="button"
            onClick={onClose}
            aria-label="Close stats"
          >
            <X size={18} />
          </button>
        </header>

        <section className="post-detail-panel">
          <div className="post-detail-media">
            {livePost.media ? (
              mediaIsVideo ? (
                <video src={`${API_BASE_URL}${livePost.media.url}`} controls muted />
              ) : (
                <img
                  src={`${API_BASE_URL}${livePost.media.url}`}
                  alt={livePost.media.originalName || ""}
                />
              )
            ) : (
              <div className="text-tile stats-text-tile">
                <FileText size={28} />
              </div>
            )}
          </div>

          <div className="post-detail-content">
            <div className="post-detail-heading">
              <div>
                <p className="eyebrow">Post Details</p>
                <h3>{caption}</h3>
              </div>
              <span className={`publish-type-badge ${publishType}`}>
                {publishType === "scheduled" ? <CalendarClock size={13} /> : <Zap size={13} />}
                {publishType === "scheduled" ? "Scheduled" : "Instant"}
              </span>
            </div>

            <div className="post-detail-grid">
              <span>
                <small>Account</small>
                <strong>{accountLabelForPost(livePost)}</strong>
              </span>
              <span>
                <small>Created</small>
                <strong>{new Date(livePost.createdAt).toLocaleString()}</strong>
              </span>
              <span>
                <small>Media</small>
                <strong>{mediaType}</strong>
              </span>
              <span>
                <small>File Size</small>
                <strong>{formatBytes(livePost.media?.size)}</strong>
              </span>
              <span>
                <small>Caption</small>
                <strong>{captionWordCount} words</strong>
              </span>
              <span>
                <small>Last Refreshed</small>
                <strong>{refreshedAt}</strong>
              </span>
            </div>
          </div>
        </section>

        <section className="overall-stats-panel">
          <div className="overall-stats-heading">
            <div>
              <p className="eyebrow">All Platform Stats</p>
              <h3>Overall business metrics</h3>
            </div>
            <div className="stats-refresh-actions">
              <span className="live-sync-badge">
                {isRefreshing ? <Loader2 className="spin" size={14} /> : <CalendarClock size={14} />}
                {refreshState}; auto every 3h
              </span>
              <button
                className="stats-refresh-button"
                type="button"
                onClick={refreshMetrics}
                disabled={isRefreshing || availablePlatforms.length === 0}
              >
                {isRefreshing ? <Loader2 className="spin" size={14} /> : <RefreshCw size={14} />}
                Refresh now
              </button>
            </div>
          </div>
          <div className="overall-stat-grid">
            {metricLabels.map(([metricKey, label, description]) => (
              (() => {
                const metric = aggregateMetric(visiblePlatformMetrics, metricKey);

                return (
                  <article className="stats-card primary-stat" key={metricKey}>
                    <BarChart3 size={18} />
                    <span>{label}</span>
                    <strong>{formatMetricValue(metric.value, metric.unavailable)}</strong>
                    <small className="metric-description">{description}</small>
                  </article>
                );
              })()
            ))}
          </div>
        </section>

        <section className="platform-detail-panel">
          <div className="platform-detail-header">
            <div>
              <p className="eyebrow">Platform Details</p>
              <h3>Inspect a platform</h3>
            </div>
            <label>
              <span>Show</span>
              <select
                value={detailPlatform}
                onChange={(event) => setDetailPlatform(event.target.value)}
              >
                <option value="all">All platforms</option>
                {availablePlatforms.map((platform) => (
                  <option key={platform} value={platform}>
                    {platformStyles[platform]?.name || platform}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="platform-stats">
            {visibleResults.length === 0 ? (
              <p className="empty-history">No platform results saved.</p>
            ) : (
              visibleResults.map((result) => (
                  <article className="platform-stat-row" key={result.platform}>
                    {(() => {
                      const metric = platformMetrics[result.platform];
                      const remoteStatus = remoteStatusForMetric(metric);
                      const statsStatus = metric?.status === "missing" ? "unavailable" : metric?.status || "unavailable";

                      return (
                        <>
                          <div className="platform-row-header">
                            <span className={`result-pill ${result.status}`}>
                              <ResultIcon status={result.status} />
                              {platformStyles[result.platform]?.name || result.platform}
                            </span>
                            <div className="platform-status-columns">
                              <span>
                                <small>Post</small>
                                <strong className={`remote-status ${remoteStatus}`}>
                                  {formatRemoteStatus(remoteStatus)}
                                </strong>
                              </span>
                              <span>
                                <small>Stats</small>
                                <strong>{formatStatus(statsStatus)}</strong>
                              </span>
                            </div>
                          </div>
                          <div className="platform-metric-grid">
                            {metricLabels.map(([metricKey, label, description]) => (
                              <span key={metricKey}>
                                <small>{label}</small>
                                <strong>
                                  {formatMetricValue(
                                    metric?.values?.[metricKey],
                                    isMetricUnavailable(metric, metricKey)
                                  )}
                                </strong>
                                <small className="metric-description">{description}</small>
                              </span>
                            ))}
                          </div>
                          <p className="platform-message">
                            {formatPlatformMessage(metric?.message || result.message)}
                          </p>
                          {metric?.updatedAt && (
                            <small>Updated: {new Date(metric.updatedAt).toLocaleString()}</small>
                          )}
                          {result.remoteId && <small>Remote ID: {result.remoteId}</small>}
                        </>
                      );
                    })()}
                  </article>
              ))
            )}
          </div>
        </section>
      </section>
    </div>
  );
}

function PostItem({ post }) {
  const [showStats, setShowStats] = useState(false);
  const publishType = publishTypeForPost(post);
  const results = post.results || [];
  const platformMetrics = post.metrics?.platforms || {};
  const mediaIsVideo = post.media?.mimeType?.startsWith("video/");
  const statsLabel = `Open stats for ${post.caption || post.media?.originalName || "post"}`;

  return (
    <>
      <article className="post-item">
        <div className="post-summary">
          <button
            className="stats-thumbnail"
            type="button"
            onClick={() => setShowStats(true)}
            aria-label={statsLabel}
          >
            {post.media ? (
              mediaIsVideo ? (
                <video src={`${API_BASE_URL}${post.media.url}`} muted />
              ) : (
                <img src={`${API_BASE_URL}${post.media.url}`} alt="" />
              )
            ) : (
              <div className="text-tile">
                <FileText size={22} />
              </div>
            )}
            <span className="stats-thumbnail-icon" aria-hidden="true">
              <BarChart3 size={14} />
            </span>
          </button>
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
          {results.map((result) => {
            const metric = platformMetrics[result.platform];
            const statsStatus = metric?.status === "missing" ? "unavailable" : metric?.status;
            const remoteStatus = remoteStatusForMetric(metric);
            const postStatusText =
              remoteStatus !== "unknown" ? ` Post: ${formatRemoteStatus(remoteStatus)}.` : "";
            const analyticsStatus = statsStatus ? ` Stats: ${formatStatus(statsStatus)}.` : "";

            return (
              <span
                className={`result-pill ${result.status}`}
                key={result.platform}
                title={`${result.message || ""}${postStatusText}${analyticsStatus}`.trim()}
              >
                <ResultIcon status={result.status} />
                {platformStyles[result.platform]?.name || result.platform}
              </span>
            );
          })}
        </div>
      </article>

      {showStats && (
        <PostStatsModal
          post={post}
          publishType={publishType}
          onClose={() => setShowStats(false)}
        />
      )}
    </>
  );
}

export default PostItem;
