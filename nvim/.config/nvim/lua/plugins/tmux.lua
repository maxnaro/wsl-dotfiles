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
      { "<M-h>", "<cmd>TmuxNavigateLeft<cr>", desc = "Navigate Left (Vim/Tmux)" },
      { "<M-j>", "<cmd>TmuxNavigateDown<cr>", desc = "Navigate Down (Vim/Tmux)" },
      { "<M-k>", "<cmd>TmuxNavigateUp<cr>", desc = "Navigate Up (Vim/Tmux)" },
      { "<M-l>", "<cmd>TmuxNavigateRight<cr>", desc = "Navigate Right (Vim/Tmux)" },
      { "<M-\\>", "<cmd>TmuxNavigatePrevious<cr>", desc = "Navigate Previous (Vim/Tmux)" },
    },
  },
}
