import { useState } from "react";
import { useStores } from "@/stores/StoreContext";
import { API_BASE_URL } from "@/api/client";

interface SecureImageProps {
  fileId: string;
  className?: string;
  alt?: string;
}

export function SecureImage({ fileId, className, alt }: SecureImageProps) {
  const { authStore } = useStores();
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (!authStore.token) {
    return <div className={`bg-muted animate-pulse ${className ?? ""}`} />;
  }

  // Pass the token as a query parameter so the browser can natively load and redirect to S3
  // without triggering CORS blocks caused by fetch + Authorization header on redirects.
  const srcUrl = `${API_BASE_URL}/receipts/images/${fileId}?token=${authStore.token}`;

  return (
    <>
      {!loaded && !error && <div className={`bg-muted animate-pulse ${className ?? ""}`} />}
      {error && (
        <div
          className={`bg-muted flex items-center justify-center text-xs text-muted-foreground ${className ?? ""}`}
        >
          Failed to load
        </div>
      )}
      {!error && (
        <img
          src={srcUrl}
          alt={alt}
          className={`${className ?? ""} ${loaded ? "block" : "hidden"}`}
          onLoad={() => {
            setLoaded(true);
          }}
          onError={() => {
            setLoaded(true);
            setError(true);
          }}
        />
      )}
    </>
  );
}
