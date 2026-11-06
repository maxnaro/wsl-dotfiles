;;; $DOOMDIR/config.el -*- lexical-binding: t; -*-

;; Colors match nvim/lua/config/palette.lua and the terminal's Chocolatier scheme.
(setq doom-theme 'doom-chocolatier
      display-line-numbers-type t
      org-directory "~/org/")

;; Block lettering matches the ViMax dashboard, without the sleeping Zs.
;; Doom centers the whole multiline banner, preserving its shared left edge.
(defun emax-dashboard-banner ()
  "Return the EMax dashboard wordmark."
  (propertize
   (mapconcat
    #'identity
    '("███████╗███╗   ███╗"
      "██╔════╝████╗ ████║"
      "█████╗  ██╔████╔██║ ██████╗██╗ ██╗"
      "██╔══╝  ██║╚██╔╝██║██╔══██║╚████╔╝"
      "███████╗██║ ╚═╝ ██║╚██████║██╔═██╗"
      "╚══════╝╚═╝     ╚═╝ ╚═════╝╚═╝ ╚═╝")
    "\n")
   'face '+dashboard-banner))

(setq fancy-splash-image nil
      +dashboard-ascii-banner-fn #'emax-dashboard-banner)

;; In terminals inherit the terminal's background, including its opacity.
;; In GUI frames alpha-background leaves text opaque (Emacs 29+).
(defun emax-transparent-frame (&optional frame)
  "Make FRAME's main background transparent without fading its text."
  (let ((frame (or frame (selected-frame))))
    (if (display-graphic-p frame)
        (set-frame-parameter frame 'alpha-background 0)
      (set-frame-parameter frame 'background-color "unspecified-bg")
      (dolist (face '(default fringe line-number line-number-current-line
                      mode-line mode-line-active mode-line-inactive header-line
                      solaire-default-face solaire-fringe-face
                      solaire-line-number-face solaire-hl-line-face
                      solaire-mode-line-face solaire-mode-line-active-face
                      solaire-mode-line-inactive-face solaire-header-line-face))
        (when (facep face)
          (set-face-background face "unspecified-bg" frame))))))

(defun emax-refresh-transparency ()
  "Restore transparency in existing frames after loading a theme."
  (mapc #'emax-transparent-frame (frame-list)))

(add-hook 'after-make-frame-functions #'emax-transparent-frame)
(add-hook 'doom-load-theme-hook #'emax-refresh-transparency t)
(emax-refresh-transparency)
