/** Longest side a photo is sent at: the server reads at most this much anyway. */
export const SENT_PHOTO_SIDE = 3000;
const QUALITY = 0.9;

/**
 * A receipt photo made small enough to send quickly (F23.6): upright, JPEG, at most
 * 3000 px on its longest side — about 1 MB where a phone's original is 4-5 MB. On a phone
 * network that is most of the wait, and it keeps a long receipt in many shots under the
 * 32 MB a request may carry. Anything the browser cannot draw (a PDF, HEIC outside
 * Safari), or a photo already small, goes as it was.
 */
export async function shrinkPhoto(file: File): Promise<File> {
  if (!file.type.startsWith("image/") || typeof createImageBitmap !== "function") return file;
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    return file;
  }
  try {
    const scale = Math.min(1, SENT_PHOTO_SIDE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.type === "image/jpeg" && file.size < 1_500_000) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", QUALITY);
    });
    if (!blob || blob.size >= file.size) return file;
    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg", lastModified: file.lastModified });
  } finally {
    bitmap.close();
  }
}
