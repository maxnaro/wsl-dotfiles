;;; doom-chocolatier-theme.el --- Warm terminal-matched colors -*- lexical-binding: t; -*-
(require 'doom-themes)
(require 'seq)

(def-doom-theme doom-chocolatier
  "Chocolatier colors shared with the Neovim and terminal configuration."
  :background-mode 'dark
  ((bg '("#221A15")) (bg-alt '("#2A201A"))
   (fg '("#D3C6AA")) (fg-alt '("#5C483C"))
   (base0 bg) (base1 bg-alt) (base2 bg-alt) (base3 '("#44342A"))
   (base4 '("#5C483C")) (base5 base4) (base6 '("#907659"))
   (base7 fg) (base8 '("#F2E7C9"))
   (grey base4) (red '("#DC7062")) (orange '("#E6B450"))
   (green '("#889B4A")) (yellow orange) (blue '("#7FA2B5"))
   (dark-blue blue) (magenta '("#BC8CBC")) (violet magenta)
   (cyan '("#7EA69F")) (teal cyan) (dark-cyan cyan)
   (highlight cyan) (vertical-bar base4) (selection base3)
   (builtin cyan) (comments base6) (doc-comments base6)
   (constants magenta) (functions magenta) (keywords red)
   (methods magenta) (operators cyan) (type yellow)
   (strings green) (variables blue) (numbers magenta)
   (region selection) (error red) (warning yellow) (success green)
   (vc-modified yellow) (vc-added green) (vc-deleted red))
  ((cursor :background base8)
   (+dashboard-banner :foreground cyan)
   (mode-line :foreground fg :background bg)
   (mode-line-inactive :foreground fg-alt :background bg)))

;; Display selectors keep terminal backgrounds transparent even when GUI and
;; terminal frames share a daemon. Selection and popup surfaces remain opaque.
(dolist (face '(default fringe line-number line-number-current-line
                mode-line mode-line-active mode-line-inactive header-line
                solaire-default-face solaire-mode-line-face
                solaire-mode-line-inactive-face))
  (let* ((setting (seq-find (lambda (entry)
                              (and (eq (car entry) 'theme-face)
                                   (eq (cadr entry) face)))
                            (get 'doom-chocolatier 'theme-settings)))
         (specs (nth 3 setting))
         (attributes (copy-sequence (cadar specs))))
    (custom-theme-set-faces
     'doom-chocolatier
     `(,face ((((type tty))
               ,(plist-put attributes :background "unspecified-bg"))
              ,@(or specs '((t (:background "#221A15")))))))))

(provide-theme 'doom-chocolatier)
;;; doom-chocolatier-theme.el ends here
