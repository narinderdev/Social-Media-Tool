import { useEffect, useMemo, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { apiFetch, parseJsonResponse } from "./api";
import ConfirmModal from "./components/ConfirmModal";
import DashboardView from "./components/DashboardView";
import HistoryView from "./components/HistoryView";
import LoadingScreen from "./components/LoadingScreen";
import LoginPage from "./components/LoginPage";
import Sidebar from "./components/Sidebar";
import { APP_NAME, initialForm, platformStyles } from "./constants";
import { availablePlatformKeys, currentRoute, errorMessages } from "./utils";

function App() {
  const [form, setForm] = useState(initialForm);
  const [platforms, setPlatforms] = useState([]);
  const [posts, setPosts] = useState([]);
  const [previewUrl, setPreviewUrl] = useState("");
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authStatus, setAuthStatus] = useState("checking");
  const [user, setUser] = useState(null);
  const [route, setRoute] = useState(currentRoute);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [sessionError, setSessionError] = useState("");

  const selectedPlatformLabels = useMemo(
    () =>
      form.platforms
        .map((platform) => platformStyles[platform]?.name || platform)
        .join(", "),
    [form.platforms]
  );

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      if (authStatus !== "authenticated") {
        window.history.replaceState({}, "", "/login");
        return;
      }

      if (!["/dashboard", "/posts"].includes(window.location.pathname)) {
        window.history.replaceState({}, "", "/dashboard");
      }
      setRoute(currentRoute());
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [authStatus]);

  useEffect(() => {
    if (!form.media) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreviewUrl = URL.createObjectURL(form.media);
    setPreviewUrl(nextPreviewUrl);
    return () => URL.revokeObjectURL(nextPreviewUrl);
  }, [form.media]);

  const handleUnauthorized = () => {
    setAuthStatus("anonymous");
    setUser(null);
    setPosts([]);
    setPlatforms([]);
    setErrors([]);
    window.history.replaceState({}, "", "/login");
  };

  const checkSession = async () => {
    setAuthStatus("checking");
    setSessionError("");
    try {
      const response = await apiFetch("/api/auth/session");
      const data = await response.json();
      if (!response.ok || !data.user) {
        handleUnauthorized();
        return;
      }

      setUser(data.user);
      setAuthStatus("authenticated");
      if (!["/dashboard", "/posts"].includes(window.location.pathname)) {
        window.history.replaceState({}, "", "/dashboard");
      }
      setRoute(currentRoute());
      await loadDashboard(true);
    } catch {
      setAuthStatus("unavailable");
      setSessionError("Backend is not reachable. Start the API server first, then retry.");
    }
  };

  const loadDashboard = async (sessionConfirmed = false) => {
    if (!sessionConfirmed && authStatus !== "authenticated") {
      return;
    }

    setLoading(true);
    setErrors([]);

    try {
      const [platformResponse, postsResponse] = await Promise.all([
        apiFetch("/api/platforms"),
        apiFetch("/api/posts")
      ]);

      if (platformResponse.status === 401 || postsResponse.status === 401) {
        handleUnauthorized();
        return;
      }

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

  const navigate = (nextRoute) => {
    const path = nextRoute === "posts" ? "/posts" : "/dashboard";
    window.history.pushState({}, "", path);
    setRoute(nextRoute);
  };

  const upsertPost = (post) => {
    setPosts((current) => [post, ...current.filter((item) => item.id !== post.id)]);
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
      const response = await apiFetch("/api/posts", {
        method: "POST",
        body: payload
      });
      const data = await response.json();

      if (response.status === 401) {
        handleUnauthorized();
        return;
      }

      if (!response.ok) {
        const partialPost = data.post || data.detail?.post;
        if (partialPost) {
          upsertPost(partialPost);
          setForm({ ...initialForm, platforms: availablePlatformKeys(platforms) });
        }
        setErrors(errorMessages(data));
        return;
      }

      upsertPost(data.post);
      setForm({ ...initialForm, platforms: availablePlatformKeys(platforms) });
    } catch {
      setErrors(["Post request failed. Check that the backend is running."]);
    } finally {
      setSubmitting(false);
    }
  };

  const login = async (credentials) => {
    const data = await parseJsonResponse(
      await apiFetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials)
      })
    );

    setUser(data.user);
    setAuthStatus("authenticated");
    window.history.replaceState({}, "", "/dashboard");
    setRoute("dashboard");
    await loadDashboard(true);
  };

  const logout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    setShowLogoutModal(false);
    handleUnauthorized();
  };

  const canSubmit = form.platforms.length > 0 && (form.caption.trim() || form.media);

  if (authStatus === "checking") {
    return <LoadingScreen />;
  }

  if (authStatus === "unavailable") {
    return (
      <LoadingScreen
        message="Cannot verify admin session"
        error={sessionError}
        onRetry={checkSession}
      />
    );
  }

  if (authStatus !== "authenticated") {
    return <LoginPage onLogin={login} />;
  }

  return (
    <div className="app-layout">
      <Sidebar
        route={route}
        user={user}
        onNavigate={navigate}
        onLogout={() => setShowLogoutModal(true)}
      />

      <main className="app-shell">
        <header className="top-bar">
          <div>
            <p className="eyebrow">{APP_NAME}</p>
            <h1>{route === "posts" ? "Post History" : "Composer"}</h1>
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

        {route === "posts" ? (
          <HistoryView posts={posts} loading={loading} />
        ) : (
          <DashboardView
            form={form}
            platforms={platforms}
            previewUrl={previewUrl}
            selectedPlatformLabels={selectedPlatformLabels}
            canSubmit={canSubmit}
            submitting={submitting}
            setForm={setForm}
            updateTextOnly={updateTextOnly}
            updatePlatform={updatePlatform}
            submitPost={submitPost}
          />
        )}
      </main>

      {showLogoutModal && (
        <ConfirmModal
          title="Log out?"
          message="Are you sure you want to end this admin session?"
          confirmLabel="Logout"
          onCancel={() => setShowLogoutModal(false)}
          onConfirm={logout}
        />
      )}
    </div>
  );
}

export default App;
