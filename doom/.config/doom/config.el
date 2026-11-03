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
