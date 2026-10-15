return {
  {
    "christoomey/vim-tmux-navigator",
    cmd = {
      "TmuxNavigateLeft",
      "TmuxNavigateDown",
      "TmuxNavigateUp",
      "TmuxNavigateRight",
      "TmuxNavigatePrevious",
      "TmuxNavigatorProcessList",
    },
    keys = {
      { "<c-h>", "<cmd><C-U>TmuxNavigateLeft<cr>", desc = "Navigate Left (Vim/Tmux)" },
      { "<c-j>", "<cmd><C-U>TmuxNavigateDown<cr>", desc = "Navigate Down (Vim/Tmux)" },
      { "<c-k>", "<cmd><C-U>TmuxNavigateUp<cr>", desc = "Navigate Up (Vim/Tmux)" },
      { "<c-l>", "<cmd><C-U>TmuxNavigateRight<cr>", desc = "Navigate Right (Vim/Tmux)" },
      { "<c-\\>", "<cmd><C-U>TmuxNavigatePrevious<cr>", desc = "Navigate Previous (Vim/Tmux)" },
    },
  },
}
