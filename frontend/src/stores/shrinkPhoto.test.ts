import { afterEach, describe, expect, it, vi } from "vitest";

import { SENT_PHOTO_SIDE, shrinkPhoto } from "./shrinkPhoto";

function fakeCanvas() {
  const sizes: { width: number; height: number }[] = [];
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (
    this: HTMLCanvasElement,
  ) {
    sizes.push({ width: this.width, height: this.height });
    return { drawImage: vi.fn() } as unknown as CanvasRenderingContext2D;
  });
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((done) => {
    done(new Blob(["small"], { type: "image/jpeg" }));
  });
  return sizes;
}

describe("shrinkPhoto", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends a phone original as a JPEG at most 3000 px on its longest side", async () => {
    const close = vi.fn();
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn().mockResolvedValue({ width: 4032, height: 3024, close }),
    );
    const sizes = fakeCanvas();
    const original = new File([new Uint8Array(4_600_000)], "IMG_0001.HEIC", { type: "image/heic" });

    const sent = await shrinkPhoto(original);

    expect(sizes).toEqual([{ width: SENT_PHOTO_SIDE, height: 2250 }]);
    expect(sent.type).toBe("image/jpeg");
    expect(sent.name).toBe("IMG_0001.jpg");
    expect(sent.size).toBeLessThan(original.size);
    expect(close).toHaveBeenCalled();
  });

  it("sends a PDF, or a photo the browser cannot draw, as it was", async () => {
    vi.stubGlobal("createImageBitmap", vi.fn().mockRejectedValue(new Error("cannot decode")));
    const pdf = new File(["%PDF"], "r.pdf", { type: "application/pdf" });
    const heic = new File(["x"], "r.heic", { type: "image/heic" });

    expect(await shrinkPhoto(pdf)).toBe(pdf);
    expect(await shrinkPhoto(heic)).toBe(heic);
  });

  it("leaves a small JPEG alone", async () => {
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn().mockResolvedValue({ width: 1200, height: 1600, close: vi.fn() }),
    );
    const small = new File([new Uint8Array(400_000)], "r.jpg", { type: "image/jpeg" });

    expect(await shrinkPhoto(small)).toBe(small);
  });
});
