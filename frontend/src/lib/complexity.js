import { i18n } from '../i18n'

/** Lowest to highest — mirrors COMPLEXITY_LEVELS in backend/app/models.py. */
export const COMPLEXITY_LEVELS = ['coffee', 'easy', 'normal', 'difficult', 'very_difficult', 'unknown']

export const DEFAULT_COMPLEXITY = 'normal'

export function complexityLabel(level) {
  return i18n.global.t(`complexity.${level || DEFAULT_COMPLEXITY}`)
}
