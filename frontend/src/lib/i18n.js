import { writable, derived } from "svelte/store";
import en from "../locales/en.json";
import de from "../locales/de.json";

export const dictionaries = { en, de };

export const lang = writable("en");

export const t = derived(lang, ($lang) => {
  return (key) => {
    const dict = dictionaries[$lang] || {};
    return dict[key] ?? key;
  };
});
