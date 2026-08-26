import { useEffect, useState } from "react";
import { useStores } from "@/stores/StoreContext";

interface SecureImageProps {
  fileId: string;
  className?: string;
  alt?: string;
}

export function SecureImage({ fileId, className, alt }: SecureImageProps) {
  const { authStore } = useStores();
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let isMounted = true;

    async function fetchImage() {
      if (!authStore.token) return;

      try {
        const response = await fetch(`http://localhost:8000/receipts/images/${fileId}`, {
          headers: {
            Authorization: `Bearer ${authStore.token}`,
          },
        });

        if (response.ok && isMounted) {
          const blob = await response.blob();
          objectUrl = URL.createObjectURL(blob);
          setSrc(objectUrl);
        }
      } catch (err) {
        console.error("Failed to fetch image", err);
      }
    }

    void fetchImage();

    return () => {
      isMounted = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileId, authStore.token]);

  if (!src) return <div className={`bg-muted animate-pulse ${className ?? ""}`} />;

  return <img src={src} alt={alt} className={className} />;
}
