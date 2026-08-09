// Persists the merge parameters across visits, so a reload does not throw the
// user back to the hardcoded defaults. Named workspaces remain the way to keep
// a full setup (images included); this only remembers the knobs.
//
// Restoring is field-by-field on purpose: a stored blob is untrusted input, and
// merging a whole object would let one stale or hand-edited value corrupt the
// panel. Anything missing, unknown or out of range simply falls back to its
// default, which also means new parameters can be added without migrating.

export const STORAGE_KEY = 'oia.lastParams';

export const DEFAULT_PARAMS = {
  tileSize: 192,
  width: 6,
  sample: 1,
  outline: 0,
  removeColor: null,
  removeColorThreshold: 3,
  shadowScale: 0.0,
  useShadowImages: false,
  missingShadowPolicy: 'skipShadow',
  useBackground: false,
  skipDuplicate: true,
  previewMaxWidth: 1024,
  tileBackgroundAssignments: {},
  exportLayerMode: 'separate',
};

// Each validator returns the accepted value, or undefined to mean "reject this
// field and keep the default". Ranges mirror the backend's validate_params.
const integerIn = (min, max) => (value) => (
  Number.isInteger(value) && value >= min && value <= max ? value : undefined
);

const numberIn = (min, max) => (value) => (
  typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max
    ? value
    : undefined
);

const boolean = (value) => (typeof value === 'boolean' ? value : undefined);

const oneOf = (...allowed) => (value) => (allowed.includes(value) ? value : undefined);

// The backend's parse_remove_color takes the first six hex digits after an
// optional '#', so accept exactly what it can already handle.
const hexColorOrNull = (value) => {
  if (value === null) return null;
  return typeof value === 'string' && /^#?[0-9a-fA-F]{6,8}$/.test(value) ? value : undefined;
};

const VALIDATORS = {
  tileSize: integerIn(1, 512),
  width: integerIn(1, 20),
  sample: integerIn(1, Number.MAX_SAFE_INTEGER),
  outline: integerIn(0, 50),
  removeColor: hexColorOrNull,
  removeColorThreshold: integerIn(0, 255),
  shadowScale: numberIn(0, 5),
  useShadowImages: boolean,
  missingShadowPolicy: oneOf('skipShadow', 'ignoreSprite', 'fail'),
  useBackground: boolean,
  skipDuplicate: boolean,
  previewMaxWidth: integerIn(256, 4096),
  exportLayerMode: oneOf('separate', 'combined'),
};

// tileBackgroundAssignments is deliberately absent: its keys are sprite
// filenames, and the sprites themselves are not persisted here, so restoring it
// would point every assignment at a tile that no longer exists.
export const PERSISTED_KEYS = Object.keys(VALIDATORS);

// localStorage throws rather than returning null when storage is disabled
// (Safari private browsing, blocked third-party contexts), and is absent
// altogether outside the browser.
const getStorage = () => {
  try {
    return typeof window !== 'undefined' && window.localStorage ? window.localStorage : null;
  } catch (e) {
    return null;
  }
};

export const loadStoredParams = () => {
  const defaults = { ...DEFAULT_PARAMS };
  const storage = getStorage();
  if (!storage) return defaults;

  let stored;
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    stored = JSON.parse(raw);
  } catch (e) {
    return defaults;
  }

  if (!stored || typeof stored !== 'object' || Array.isArray(stored)) return defaults;

  PERSISTED_KEYS.forEach(key => {
    if (!Object.prototype.hasOwnProperty.call(stored, key)) return;
    const accepted = VALIDATORS[key](stored[key]);
    if (accepted !== undefined) defaults[key] = accepted;
  });

  return defaults;
};

export const saveParams = (params) => {
  const storage = getStorage();
  if (!storage || !params) return;

  const payload = {};
  PERSISTED_KEYS.forEach(key => {
    if (Object.prototype.hasOwnProperty.call(params, key)) payload[key] = params[key];
  });

  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (e) {
    // A full or read-only quota must not break the merge that just succeeded.
  }
};

export const clearStoredParams = () => {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(STORAGE_KEY);
  } catch (e) {
    // Nothing to do — the next save will overwrite whatever survived.
  }
};
