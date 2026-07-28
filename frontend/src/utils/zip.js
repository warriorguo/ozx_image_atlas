// Minimal reader for the ZIP archives the backend produces on layered export.
// Entries are written uncompressed (ZIP_STORED), so unpacking is a header walk
// and a slice — no zip library needed.

const LOCAL_FILE_HEADER = 0x04034b50;
const HEADER_SIZE = 30;

export const unzipStored = async (blob) => {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const decoder = new TextDecoder();
  const entries = [];

  let offset = 0;
  while (offset + HEADER_SIZE <= bytes.length &&
         view.getUint32(offset, true) === LOCAL_FILE_HEADER) {
    const method = view.getUint16(offset + 8, true);
    if (method !== 0) {
      throw new Error('Unsupported compressed archive from server');
    }
    const size = view.getUint32(offset + 18, true);
    const nameLength = view.getUint16(offset + 26, true);
    const extraLength = view.getUint16(offset + 28, true);
    const nameStart = offset + HEADER_SIZE;
    const dataStart = nameStart + nameLength + extraLength;

    entries.push({
      name: decoder.decode(bytes.subarray(nameStart, nameStart + nameLength)),
      blob: new Blob([bytes.slice(dataStart, dataStart + size)], { type: 'image/png' }),
    });

    offset = dataStart + size;
  }

  if (entries.length === 0) {
    throw new Error('Export archive was empty or unreadable');
  }

  return entries;
};
