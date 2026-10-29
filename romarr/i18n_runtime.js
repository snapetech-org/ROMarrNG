/* Shared localization primitives for the inline UI and public auth pages.
   Keep this file dependency-free so the container still needs no asset build. */
(function (root) {
  'use strict';

  const RTL_FALLBACK = ['ar', 'fa', 'he'];
  const isolate = value => '\u2068' + String(value ?? '').replace(/[\u202a-\u202e\u2066-\u2069]/g, '') + '\u2069';
  const normalizeTag = value => String(value || '').trim().replace(/_/g, '-').toLowerCase();
  const matchingTag = (values, requested) => {
    if (values && Object.hasOwn(values, requested)) return requested;
    return Object.keys(values || {}).find(
      value => normalizeTag(value) === normalizeTag(requested));
  };

  function localeChain(catalog, requested) {
    const aliases = catalog?.aliases || {};
    const parents = catalog?.regionalParents || {};
    const base = catalog?.baseLocale || 'en';
    let current = normalizeTag(requested);
    const chain = [];
    const add = value => {
      const normalized = normalizeTag(value);
      if (normalized && !chain.includes(normalized)) chain.push(normalized);
    };
    for (let depth = 0; current && depth < 8; depth++) {
      add(current);
      const alias = Object.keys(aliases).find(key => normalizeTag(key) === current);
      const aliasTarget = alias ? normalizeTag(aliases[alias]) : '';
      if (aliasTarget && aliasTarget !== current) {
        current = aliasTarget;
        continue;
      }
      const parentKey = Object.keys(parents).find(key => normalizeTag(key) === current);
      const parent = parentKey ? normalizeTag(parents[parentKey]) : '';
      if (parent && parent !== current) {
        current = parent;
        continue;
      }
      const hyphen = current.lastIndexOf('-');
      if (hyphen > 0) {
        current = current.slice(0, hyphen);
        continue;
      }
      break;
    }
    add(base);
    return chain;
  }

  function resolveLocale(preferences, catalog, selectable) {
    const offered = selectable || catalog?.availableLocales || ['en'];
    const allowed = new Map(offered.map(value => [normalizeTag(value), value]));
    for (const preference of preferences || []) {
      const candidate = normalizeTag(preference);
      if (!candidate) continue;
      for (const part of localeChain(catalog, candidate)) {
        if (allowed.has(part)) return allowed.get(part);
      }
      // Chinese script is semantically significant even when the device only
      // reports a region or a bare language tag.
      if (candidate === 'zh' || candidate.startsWith('zh-')) {
        const parts = candidate.split('-');
        const traditional = parts.includes('hant') || ['tw', 'hk', 'mo'].includes(parts.at(-1));
        const chinese = traditional ? 'zh-hant' : 'zh-hans';
        for (const part of localeChain(catalog, chinese))
          if (allowed.has(part)) return allowed.get(part);
      }
      // Prefer the explicitly regional Spanish fallback for Latin American
      // browser locales. Generic Spanish continues to use the Spain catalog.
      if (candidate.startsWith('es-') && !candidate.startsWith('es-419-')) {
        const region = candidate.split('-').at(-1);
        if (['ar', 'bo', 'cl', 'co', 'cr', 'cu', 'do', 'ec', 'gt', 'hn',
          'mx', 'ni', 'pa', 'pe', 'pr', 'py', 'sv', 'uy', 've'].includes(region)
          && allowed.has('es-419')) return allowed.get('es-419');
      }
    }
    return allowed.has('en') ? allowed.get('en') : [...allowed.values()][0] || 'en';
  }

  const isRTL = (locale, catalog) => {
    const base = normalizeTag(locale).split('-')[0];
    const configured = (catalog?.rtlLocales || RTL_FALLBACK).map(normalizeTag);
    return configured.includes(base);
  };

  function messageIndex(catalog) {
    if (!catalog || !catalog.messages) return {messages: {}, sources: {}};
    let cached = catalog.__runtimeIndex;
    if (cached) return cached;
    const sources = Object.create(null);
    for (const [id, message] of Object.entries(catalog.messages)) {
      if (message && typeof message.source === 'string') sources[message.source] = id;
    }
    cached = {messages: catalog.messages, sources};
    try { Object.defineProperty(catalog, '__runtimeIndex', {value: cached}); } catch (_) {}
    return cached;
  }

  function lookup(catalog, keyOrSource, locale) {
    const index = messageIndex(catalog);
    const key = Object.hasOwn(index.messages, keyOrSource)
      ? keyOrSource : index.sources[keyOrSource];
    const entry = key ? index.messages[key] : null;
    if (!entry) return {value: String(keyOrSource ?? ''), translated: false, locale: 'en', key: null};
    for (const tag of localeChain(catalog, locale)) {
      const translationTag = matchingTag(entry.translations, tag);
      const value = translationTag ? entry.translations[translationTag] : undefined;
      if (typeof value === 'string' && value.trim()) {
        return {value, translated: normalizeTag(translationTag) !== normalizeTag(catalog.baseLocale || 'en'), locale: translationTag, key};
      }
      if (value && typeof value === 'object') {
        return {value, translated: normalizeTag(translationTag) !== normalizeTag(catalog.baseLocale || 'en'), locale: translationTag, key};
      }
    }
    return {value: entry.source, translated: false, locale: catalog.baseLocale || 'en', key};
  }

  function formatMessage(template, values, locale, formatLocale, resolveNested) {
    const args = values && typeof values === 'object' ? values : {};
    const plural = template && typeof template === 'object' && template.kind === 'plural';
    let source = template;
    let renderedArgs = args;
    if (plural) {
      const argument = String(template.argument || 'count');
      const number = Number(args[argument]);
      const forms = template.forms && typeof template.forms === 'object' ? template.forms : {};
      const exact = Number.isFinite(number) ? forms['=' + number] : null;
      const category = Number.isFinite(number)
        ? new Intl.PluralRules(locale || 'en').select(number) : 'other';
      source = exact || forms[category] || forms.other || '';
      if (Number.isFinite(number)) {
        const formatted = new Intl.NumberFormat(formatLocale || locale || 'en').format(number);
        source = String(source).replace(/#/g, isolate(formatted));
        renderedArgs = {...args, [argument]: formatted};
      }
    }
    if (typeof source !== 'string') return '';
    return source.replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (token, name) => {
      if (!Object.hasOwn(renderedArgs, name)) return token;
      const value = renderedArgs[name];
      if (value && typeof value === 'object' && typeof value.source === 'string') {
        const nested = resolveNested
          ? resolveNested(value.source, value.values || {}) : value.source;
        return isolate(nested);
      }
      return isolate(value ?? '');
    });
  }

  function translate(catalog, keyOrSource, locale, values, formatLocale, resolveNested) {
    const found = lookup(catalog, keyOrSource, locale);
    return formatMessage(found.value, values || {}, locale || 'en', formatLocale,
      resolveNested) || (typeof found.value === 'string' ? found.value : '');
  }

  function normalizeDigits(value) {
    const ranges = [0x0660, 0x06f0, 0x0966, 0x09e6, 0x0a66, 0x0ae6,
      0x0b66, 0x0be6, 0x0c66, 0x0ce6, 0x0d66, 0x0de6, 0x0e50,
      0x0ed0, 0x0f20, 0x1040, 0x1090, 0x17e0, 0x1810, 0xff10];
    return Array.from(String(value ?? ''), character => {
      const point = character.codePointAt(0);
      for (const zero of ranges) if (point >= zero && point <= zero + 9)
        return String(point - zero);
      return character;
    }).join('');
  }

  root.ROMarrI18n = Object.freeze({
    localeChain, resolveLocale, isRTL, lookup, translate, formatMessage,
    normalizeDigits, isolate,
  });
})(typeof window === 'undefined' ? globalThis : window);
