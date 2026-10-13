# Purchase Entry Design Tokens

These tokens preserve the values already used by `frontend/src/pages/purchases/new.astro`. CSS color, font, radius, and spacing values below were moved without changing their rendered values. The page's HTML `theme-color` remains inline because metadata cannot consume a CSS custom property.

| Token | Raw value | Original `new.astro` source |
| --- | --- | --- |
| `color-scheme` | `light` | `:root` |
| `--color-text-primary` | `#1d302a` | `:root --ink` |
| `--color-text-muted` | `#687970` | `:root --muted` |
| `--color-border-subtle` | `#d6e1d7` | `:root --line` |
| `--color-surface-page` | `#fbfdf8` | `:root --paper` |
| `--color-action-primary` | `#1c5947` | `:root --forest` |
| `--color-action-primary-hover` | `#154536` | `:root --forest-dark` |
| `--color-action-accent` | `#cb5f49` | `:root --coral` |
| `--color-background-page` | `#eaf1e9` | `:root --wash`; `<meta name="theme-color">` |
| `--color-profile-text` | `#43584f` | `.profile-label`, `.result-date`, `.result-basis`, `.result-document` |
| `--color-profile-indicator` | `#62a681` | `.profile-dot` |
| `--color-eyebrow-divider` | `#99a99e` | `.eyebrow span` |
| `--color-mode-border` | `#b9cbbd` | `.mode-switch` |
| `--color-mode-surface` | `#f6faf4` | `.mode-switch` |
| `--color-mode-text` | `#52675b` | `.mode-button` |
| `--color-panel-border` | `#d8e2d8` | `.entry-layout` |
| `--color-step-border` | `#b8cbbd` | `.step-number` |
| `--color-upload-border` | `#9db8a5` | `.file-drop` |
| `--color-upload-surface` | `#f4f8f2` | `.file-drop` |
| `--color-upload-surface-hover` | `#edf5ec` | `.file-drop:hover`, `.file-drop:focus-within`, `.file-drop.is-dragging` |
| `--color-document-icon-surface` | `#dcebe0` | `.document-icon` |
| `--color-upload-separator` | `#91a59a` | `.footnote-separator` |
| `--color-action-disabled` | `#aab9af` | `.preview-button:disabled` |
| `--color-action-pending` | `#687f71` | `.preview-button.is-pending` |
| `--color-privacy-text` | `#5d7668` | `.privacy-note` |
| `--color-privacy-indicator` | `#68a57d` | `.privacy-mark` |
| `--color-result-surface` | `#eff5ed` | `.warranty-result` |
| `--color-field-label` | `#40564b` | `.field` |
| `--color-text-subtle` | `#84948b` | `.field em`, `.field select:invalid` |
| `--color-field-warning` | `#9c5b33` | `.field-warning` |
| `--color-field-border` | `#ccd8ce` | `.field input`, `.field select` |
| `--color-feedback-error` | `#a53f35` | `.status-message.is-error` |
| `--color-required-note` | `#7b8b81` | `.required-note` |
| `--color-save-hover` | `#b94e3a` | `.save-button:hover:not(:disabled)` |
| `--color-save-disabled` | `#c3c9c2` | `.save-button:disabled` |
| `--color-footer-text` | `#708078` | `.page-footer` |
| `--color-topbar-divider` | `rgb(29 48 42 / 18%)` | `.topbar` |
| `--color-profile-indicator-ring` | `rgb(98 166 129 / 15%)` | `.profile-dot` |
| `--color-file-action-border` | `#a9c2ae` | `.choose-file` |
| `--color-surface-control` | `white` | `.choose-file`, `.field input`, `.field select` |
| `--color-on-action` | `white` | `.mode-button[aria-pressed="true"]`, `.preview-button`, `.save-button` |
| `--color-page-pattern` | `rgb(28 89 71 / 3%)` | `body` background image |
| `--color-panel-shadow` | `rgb(35 62 49 / 7%)` | `.entry-layout` box shadow |
| `--color-field-focus-ring` | `rgb(28 89 71 / 12%)` | `.field input:focus`, `.field select:focus` |
| `--color-focus-visible` | `rgb(203 95 73 / 60%)` | `:focus-visible` |
| `--font-sans` | `"Aptos", "Trebuchet MS", sans-serif` | `:root --sans` |
| `--font-serif` | `"Palatino Linotype", "Book Antiqua", Georgia, serif` | `:root --serif` |
| `--radius-brand-mark` | `7px 7px 7px 2px` | `.brand-mark` |
| `--radius-mode-switch` | `6px` | `.mode-switch` |
| `--radius-mode-button` | `4px` | `.mode-button` |
| `--radius-panel` | `8px` | `.entry-layout` |
| `--radius-round` | `50%` | `.profile-dot`, `.step-number`, `.footnote-separator` |
| `--radius-upload-target` | `6px` | `.file-drop` |
| `--radius-document-icon` | `7px` | `.document-icon` |
| `--radius-file-action` | `5px` | `.choose-file` |
| `--radius-form-control` | `4px` | `.field input`, `.field select` |
| `--radius-primary-action` | `5px` | `.preview-button`, `.save-button` |
| `--space-body-margin` | `0` | `body` `margin: 0` |
| `--space-workspace-margin` | `0 auto` | `.workspace` `margin: 0 auto` |
| `--space-brand-gap` | `11px` | `.brand` `gap: 11px` |
| `--space-profile-label-gap` | `9px` | `.profile-label` `gap: 9px` |
| `--space-page-heading-padding` | `42px 0 28px` | `.page-heading` `padding: 42px 0 28px` |
| `--space-eyebrow-margin` | `0 0 10px` | `.eyebrow` `margin: 0 0 10px` |
| `--space-eyebrow-divider-padding` | `0 7px` | `.eyebrow span` `padding: 0 7px` |
| `--space-heading-copy-margin` | `9px 0 0` | `.heading-copy` `margin: 9px 0 0` |
| `--space-page-title-margin` | `0` | `h1` `margin: 0` |
| `--space-mode-switch-margin` | `0 0 16px` | `.mode-switch` `margin: 0 0 16px` |
| `--space-mode-switch-padding` | `3px` | `.mode-switch` `padding: 3px` |
| `--space-mode-button-padding` | `0 14px` | `.mode-button` `padding: 0 14px` |
| `--space-entry-panel-padding` | `30px` | `.upload-panel, .details-panel` `padding: 30px` |
| `--space-section-heading-gap` | `13px` | `.section-heading` `gap: 13px` |
| `--space-section-heading-margin-bottom` | `24px` | `.section-heading` `margin-bottom: 24px` |
| `--space-section-title-margin` | `2px 0 4px` | `h2` `margin: 2px 0 4px` |
| `--space-section-copy-margin` | `0` | `.section-heading p` `margin: 0` |
| `--space-file-drop-padding` | `22px 16px` | `.file-drop` `padding: 22px 16px` |
| `--space-document-icon-margin-bottom` | `13px` | `.document-icon` `margin-bottom: 13px` |
| `--space-drop-subtitle-margin-top` | `4px` | `.drop-subtitle` `margin-top: 4px` |
| `--space-choose-file-margin-top` | `14px` | `.choose-file` `margin-top: 14px` |
| `--space-choose-file-padding` | `8px 14px` | `.choose-file` `padding: 8px 14px` |
| `--space-upload-footnote-gap` | `9px` | `.upload-footnote` `gap: 9px` |
| `--space-upload-footnote-margin` | `10px 0 21px` | `.upload-footnote` `margin: 10px 0 21px` |
| `--space-preview-button-gap` | `9px` | `.preview-button` `gap: 9px` |
| `--space-privacy-note-gap` | `7px` | `.privacy-note` `gap: 7px` |
| `--space-privacy-note-margin` | `15px 0 0` | `.privacy-note` `margin: 15px 0 0` |
| `--space-status-message-margin` | `12px 0 0` | `.status-message` `margin: 12px 0 0` |
| `--space-warranty-result-gap` | `7px 20px` | `.warranty-result` `gap: 7px 20px` |
| `--space-warranty-result-margin-top` | `18px` | `.warranty-result` `margin-top: 18px` |
| `--space-warranty-result-padding` | `16px 18px` | `.warranty-result` `padding: 16px 18px` |
| `--space-result-eyebrow-margin` | `0 0 3px` | `.result-eyebrow` `margin: 0 0 3px` |
| `--space-result-title-margin` | `0` | `.warranty-result h3` `margin: 0` |
| `--space-result-copy-margin` | `0` | `.result-date, .result-basis, .result-status, .result-document` `margin: 0` |
| `--space-field-grid-gap` | `17px 15px` | `.field-grid` `gap: 17px 15px` |
| `--space-field-gap` | `7px` | `.field` `gap: 7px` |
| `--space-form-control-padding` | `0 11px` | `.field input, .field select` `padding: 0 11px` |
| `--space-optional-label-margin-left` | `4px` | `.field em` `margin-left: 4px` |
| `--space-form-rule-margin` | `23px 0 12px` | `.form-rule` `margin: 23px 0 12px` |
| `--space-required-note-margin` | `0` | `.required-note` `margin: 0` |
| `--space-form-actions-gap` | `14px` | `.form-actions` `gap: 14px` |
| `--space-save-button-gap` | `8px` | `.save-button` `gap: 8px` |
| `--space-save-button-padding` | `0 15px` | `.save-button` `padding: 0 15px` |
| `--space-page-footer-padding` | `21px 1px 30px` | `.page-footer` `padding: 21px 1px 30px` |
| `--space-focus-outline-offset` | `3px` | `:focus-visible` `outline-offset: 3px` |
| `--space-mobile-page-heading-padding` | `31px 0 23px` | `@media (max-width: 760px) .page-heading` `padding: 31px 0 23px` |
| `--space-mobile-entry-panel-padding` | `24px 21px` | `@media (max-width: 760px) .upload-panel, .details-panel` `padding: 24px 21px` |
| `--space-narrow-entry-panel-padding` | `21px 16px` | `@media (max-width: 420px) .upload-panel, .details-panel` `padding: 21px 16px` |
| `--space-narrow-page-footer-gap` | `15px` | `@media (max-width: 420px) .page-footer` `gap: 15px` |

Radius tokens retain the existing control roles. Every spacing declaration in the page stylesheet is role-tokenized, including resets and responsive overrides; only sizing/layout values that are not spacing remain local. The `theme-color` metadata stays inline because it cannot consume a CSS custom property. No contrast correction was made in this phase.