const PROXY_SAFE_UPLOAD_BYTES = 3 * 1024 * 1024;
const MAX_IMAGE_DIMENSION = 2560;

const SUPPORTED_UPLOAD_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
]);

function webpFilename(filename: string): string {
  const basename = filename.replace(/\.[^.]+$/, "") || "image";
  return `${basename}.webp`;
}

function canvasBlob(
  bitmap: ImageBitmap,
  scale: number,
  quality: number,
): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("This browser cannot prepare the selected image.");
  }

  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      blob => {
        if (blob) resolve(blob);
        else reject(new Error("The selected image could not be optimized."));
      },
      "image/webp",
      quality,
    );
  });
}

export async function prepareMediaUpload(file: File): Promise<File> {
  if (!SUPPORTED_UPLOAD_TYPES.has(file.type)) {
    throw new Error("Only JPEG, PNG, WebP or GIF images are allowed.");
  }

  if (file.size <= PROXY_SAFE_UPLOAD_BYTES) return file;

  if (file.type === "image/gif") {
    throw new Error("GIF images must be 3 MB or smaller.");
  }

  if (typeof createImageBitmap !== "function") {
    throw new Error(
      "This browser cannot optimize large images. Use a JPEG or WebP under 3 MB.",
    );
  }

  const bitmap = await createImageBitmap(file);

  try {
    const largestDimension = Math.max(bitmap.width, bitmap.height);
    let scale = Math.min(1, MAX_IMAGE_DIMENSION / largestDimension);

    for (const quality of [0.82, 0.7, 0.58]) {
      const blob = await canvasBlob(bitmap, scale, quality);
      if (blob.size <= PROXY_SAFE_UPLOAD_BYTES) {
        return new File([blob], webpFilename(file.name), {
          type: "image/webp",
          lastModified: file.lastModified,
        });
      }
      scale *= 0.8;
    }
  } finally {
    bitmap.close();
  }

  throw new Error(
    "The image is still too large after optimization. Use an image under 3 MB.",
  );
}

export const MEDIA_PROXY_SAFE_UPLOAD_BYTES = PROXY_SAFE_UPLOAD_BYTES;
