import { useEffect, useState } from "react";

interface FilePreviewProps {
  file: File;
  index: number;
  onRemove: () => void;
}

export function FilePreview({ file, index, onRemove }: FilePreviewProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    // Only create object URL for web-safe images
    if (file.type === "image/jpeg" || file.type === "image/png" || file.type === "image/webp") {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [file]);

  return (
    <span className="relative inline-flex items-center justify-center border border-border rounded-chip bg-muted w-[72px] h-[88px] overflow-hidden shrink-0">
      {previewUrl ? (
        <img
          src={previewUrl}
          alt={`Preview ${String(index + 1)}`}
          className="w-full h-full object-cover"
        />
      ) : (
        <span className="text-xs text-muted-foreground font-medium uppercase break-all p-2 text-center leading-tight">
          {file.name.split(".").pop() ?? "FILE"}
        </span>
      )}
      <span className="absolute bottom-1 right-1 text-[10px] bg-background/80 text-foreground px-1 rounded backdrop-blur-sm shadow-sm font-medium z-10 pointer-events-none">
        {index + 1}
      </span>
      <button
        onClick={onRemove}
        className="absolute top-1 left-1 bg-background border border-border rounded-full w-[18px] h-[18px] flex items-center justify-center cursor-pointer z-10 hover:bg-muted text-foreground shadow-sm"
        aria-label="Remove photo"
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </span>
  );
}
