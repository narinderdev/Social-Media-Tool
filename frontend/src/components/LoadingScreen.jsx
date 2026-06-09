import { Loader2 } from "lucide-react";

function LoadingScreen({ message = "Loading dashboard", error = "", onRetry }) {
  return (
    <main className="login-page">
      <div className="login-card compact">
        {!error && <Loader2 className="spin" size={28} />}
        <p>{message}</p>
        {error && <p className="offline-message">{error}</p>}
        {onRetry && (
          <button className="submit-button" type="button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </main>
  );
}

export default LoadingScreen;
