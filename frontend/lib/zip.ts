import JSZip from "jszip";

/**
 * Zip a folder selection (from an <input webkitdirectory>) into a Blob,
 * preserving each file's relative path so index.html lands correctly.
 */
export async function zipFolder(files: FileList | File[]): Promise<Blob> {
  const zip = new JSZip();
  const arr = Array.from(files);
  for (const file of arr) {
    // webkitRelativePath is "chosenDir/sub/index.html"; keep the sub-path.
    const rel =
      (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    zip.file(rel, file);
  }
  return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
}
