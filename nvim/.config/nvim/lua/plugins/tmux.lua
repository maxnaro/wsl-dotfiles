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
    init = function()
      vim.g.tmux_navigator_no_mappings = 1
    end,
    keys = {
      { "<M-h>", "<cmd><C-U>TmuxNavigateLeft<cr>", desc = "Navigate Left (Vim/Tmux)" },
      { "<M-j>", "<cmd><C-U>TmuxNavigateDown<cr>", desc = "Navigate Down (Vim/Tmux)" },
      { "<M-k>", "<cmd><C-U>TmuxNavigateUp<cr>", desc = "Navigate Up (Vim/Tmux)" },
      { "<M-l>", "<cmd><C-U>TmuxNavigateRight<cr>", desc = "Navigate Right (Vim/Tmux)" },
      { "<M-\\>", "<cmd><C-U>TmuxNavigatePrevious<cr>", desc = "Navigate Previous (Vim/Tmux)" },
    },
  },
}
