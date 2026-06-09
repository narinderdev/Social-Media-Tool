import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  ImagePlus,
  Loader2,
  RefreshCw,
  Send,
  UploadCloud,
  X
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:4000";

const platformStyles = {
  instagram: { name: "Instagram", tone: "rose" },
  facebook: { name: "Facebook", tone: "blue" },
  linkedin: { name: "LinkedIn", tone: "indigo" },
  twitter: { name: "X / Twitter", tone: "stone" }
};

const initialForm = {
  caption: "",
  textOnly: false,
  platforms: [],
  media: null
};

const availablePlatformKeys = (platformItems, textOnly = false, hasMedia = false) =>
  platformItems
    .filter(
      (platform) =>
        platform.configured && !((textOnly || !hasMedia) && platform.key === "instagram")
    )
    .map((platform) => platform.key);

const errorMessage = (error) => {
  if (typeof error === "string") {
    return error;
  }

  return error?.description || error?.detail || error?.message || "Could not create post.";
};

const errorMessages = (data) => {
  const errors = data.errors || data.detail || ["Could not create post."];
  return Array.isArray(errors) ? errors.map(errorMessage) : [errorMessage(errors)];
};

function App() {
  const [form, setForm] = useState(initialForm);
  const [platforms, setPlatforms] = useState([]);
  const [posts, setPosts] = useState([]);
  const [previewUrl, setPreviewUrl] = useState("");
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const selectedPlatformLabels = useMemo(
    () =>
      form.platforms
        .map((platform) => platformStyles[platform]?.name || platform)
        .join(", "),
    [form.platforms]
  );

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (!form.media) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreviewUrl = URL.createObjectURL(form.media);
    setPreviewUrl(nextPreviewUrl);
    return () => URL.revokeObjectURL(nextPreviewUrl);
  }, [form.media]);

  const loadDashboard = async () => {
    setLoading(true);
    setErrors([]);

    try {
      const [platformResponse, postsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/platforms`),
        fetch(`${API_BASE_URL}/api/posts`)
      ]);

      const platformData = await platformResponse.json();
      const postsData = await postsResponse.json();

      setPlatforms(platformData.platforms || []);
      setPosts(postsData.posts || []);
      setForm((current) => ({
        ...current,
        platforms:
          current.platforms.length > 0
            ? current.platforms.filter((platform) =>
                availablePlatformKeys(
                  platformData.platforms || [],
                  current.textOnly,
                  Boolean(current.media)
                ).includes(platform)
              )
            : availablePlatformKeys(
                platformData.platforms || [],
                current.textOnly,
                Boolean(current.media)
              )
      }));
    } catch {
      setErrors(["Backend is not reachable. Start the API server first."]);
    } finally {
      setLoading(false);
    }
  };

  const updatePlatform = (platform, checked) => {
    setForm((current) => {
      const nextPlatforms = checked
        ? [...current.platforms, platform]
        : current.platforms.filter((item) => item !== platform);

      return { ...current, platforms: [...new Set(nextPlatforms)] };
    });
  };

  const updateTextOnly = (checked) => {
    setForm((current) => ({
      ...current,
      textOnly: checked,
      media: checked ? null : current.media,
      platforms: checked
        ? current.platforms.filter((platform) => platform !== "instagram")
        : current.platforms
    }));
  };

  const submitPost = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setErrors([]);

    const payload = new FormData();
    payload.append("caption", form.caption);
    payload.append("textOnly", String(form.textOnly));
    payload.append("platforms", JSON.stringify(form.platforms));

    if (form.media && !form.textOnly) {
      payload.append("media", form.media);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/posts`, {
        method: "POST",
        body: payload
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors(errorMessages(data));
        return;
      }

      setPosts((current) => [data.post, ...current]);
      setForm({ ...initialForm, platforms: availablePlatformKeys(platforms) });
    } catch {
      setErrors(["Post request failed. Check that the backend is running."]);
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = form.platforms.length > 0 && (form.caption.trim() || form.media);

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Shared Posts</p>
          <h1>Composer</h1>
        </div>
        <button className="icon-button" type="button" onClick={loadDashboard} aria-label="Refresh">
          <RefreshCw size={18} />
        </button>
      </header>

      {errors.length > 0 && (
        <section className="alert" aria-live="polite">
          <AlertCircle size={18} />
          <div>
            {errors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        </section>
      )}

      <section className="workspace">
        <form className="composer-panel" onSubmit={submitPost}>
          <div className="panel-heading">
            <h2>New post</h2>
            <span>{selectedPlatformLabels || "No platform selected"}</span>
          </div>

          <label className="field-label" htmlFor="caption">
            Caption
          </label>
          <textarea
            id="caption"
            value={form.caption}
            onChange={(event) => setForm((current) => ({ ...current, caption: event.target.value }))}
            placeholder="Write text for the post"
            rows={7}
          />

          <div className="mode-row">
            <button
              className={!form.textOnly ? "mode-button active" : "mode-button"}
              type="button"
              onClick={() => updateTextOnly(false)}
            >
              <ImagePlus size={17} />
              Media
            </button>
            <button
              className={form.textOnly ? "mode-button active" : "mode-button"}
              type="button"
              onClick={() => updateTextOnly(true)}
            >
              <FileText size={17} />
              Text only
            </button>
          </div>

          {!form.textOnly && (
            <label className="upload-zone">
              <UploadCloud size={28} />
              <span>{form.media ? form.media.name : "Choose image or video"}</span>
              <input
                type="file"
                accept="image/*,video/*"
                onChange={(event) =>
                  setForm((current) => {
                    const media = event.target.files?.[0] || null;
                    const instagramReady = platforms.some(
                      (platform) => platform.key === "instagram" && platform.configured
                    );
                    return {
                      ...current,
                      media,
                      platforms: media
                        ? [...new Set([...current.platforms, ...(instagramReady ? ["instagram"] : [])])]
                        : current.platforms.filter((platform) => platform !== "instagram")
                    };
                  })
                }
              />
            </label>
          )}

          <fieldset>
            <legend>Platforms</legend>
            <div className="platform-grid">
              {platforms.map((platform) => {
                const disabled =
                  !platform.configured ||
                  ((form.textOnly || !form.media) && platform.key === "instagram");
                const selected = form.platforms.includes(platform.key);
                const style = platformStyles[platform.key] || { name: platform.label, tone: "stone" };

                return (
                  <label className={`platform-option ${style.tone}`} key={platform.key}>
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={disabled}
                      onChange={(event) => updatePlatform(platform.key, event.target.checked)}
                    />
                    <span>
                      <strong>{platform.label}</strong>
                      <small>{platform.configured ? "Ready" : "Needs keys"}</small>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <button className="submit-button" type="submit" disabled={!canSubmit || submitting}>
            {submitting ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            Post everywhere
          </button>
        </form>

        <aside className="preview-panel">
          <div className="panel-heading">
            <h2>Preview</h2>
            <span>{form.textOnly ? "Text" : "Media"}</span>
          </div>

          {previewUrl ? (
            form.media?.type.startsWith("video/") ? (
              <video className="media-preview" src={previewUrl} controls />
            ) : (
              <img className="media-preview" src={previewUrl} alt="" />
            )
          ) : (
            <div className="empty-preview">
              {form.textOnly ? <FileText size={42} /> : <ImagePlus size={42} />}
            </div>
          )}

          <p className="preview-caption">{form.caption || "Caption will appear here."}</p>
        </aside>
      </section>

      <section className="history">
        <div className="panel-heading">
          <h2>Post history</h2>
          <span>{loading ? "Loading" : `${posts.length} saved`}</span>
        </div>

        <div className="history-list">
          {posts.length === 0 && !loading ? (
            <p className="empty-history">No posts yet.</p>
          ) : (
            posts.map((post) => <PostItem key={post.id} post={post} />)
          )}
        </div>
      </section>
    </main>
  );
}

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
          <span className={`result-pill ${result.status}`} key={result.platform}>
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

export default App;
