import { unzipStored } from '../utils/zip';

// A real ZIP_STORED archive as produced by the export endpoint, holding
// "atlas.png" ("sprite-bytes") and "atlas_shadow.png" ("shadow-bytes-x").
const FIXTURE =
  'UEsDBBQAAAAAAEFY/FzR+0LpDAAAAAwAAAAJAAAAYXRsYXMucG5nc3ByaXRlLWJ5dGVzUEsDBBQAAAAAAEFY' +
  '/FzCkA+ODgAAAA4AAAAQAAAAYXRsYXNfc2hhZG93LnBuZ3NoYWRvdy1ieXRlcy14UEsBAhQDFAAAAAAAQVj8' +
  'XNH7QukMAAAADAAAAAkAAAAAAAAAAAAAAIABAAAAAGF0bGFzLnBuZ1BLAQIUAxQAAAAAAEFY/FzCkA+ODgAA' +
  'AA4AAAAQAAAAAAAAAAAAAACAATMAAABhdGxhc19zaGFkb3cucG5nUEsFBgAAAAACAAIAdQAAAG8AAAAAAA==';

const toBytes = (base64) => {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
};

// jsdom's Blob does not implement arrayBuffer(); back it with the raw bytes.
const asBlob = (bytes) => {
  const blob = new Blob([bytes]);
  blob.arrayBuffer = () => Promise.resolve(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
  return blob;
};

describe('unzipStored', () => {
  test('extracts every entry with its name and payload size', async () => {
    const entries = await unzipStored(asBlob(toBytes(FIXTURE)));

    expect(entries.map(e => e.name)).toEqual(['atlas.png', 'atlas_shadow.png']);
    expect(entries.map(e => e.blob.size)).toEqual(
      ['sprite-bytes'.length, 'shadow-bytes-x'.length]);
    expect(entries.every(e => e.blob.type === 'image/png')).toBe(true);
  });

  test('rejects an archive it cannot read', async () => {
    await expect(unzipStored(asBlob(new Uint8Array([1, 2, 3, 4, 5]))))
      .rejects.toThrow(/empty or unreadable/i);
  });
});
