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
      { "<M-l>", "<Esc><cmd>TmuxNavigateRight<cr>", mode = { "i", "x" }, desc = "Navigate Right (Vim/Tmux)" },
      { "<M-l>", "<C-\\><C-n><cmd>TmuxNavigateRight<cr>", mode = "t", desc = "Navigate Right (Vim/Tmux)" },
      { "<M-k>", "<Esc><cmd>TmuxNavigateUp<cr>", mode = { "i", "x" }, desc = "Navigate Up (Vim/Tmux)" },
      { "<M-k>", "<C-\\><C-n><cmd>TmuxNavigateUp<cr>", mode = "t", desc = "Navigate Up (Vim/Tmux)" },
      { "<M-j>", "<Esc><cmd>TmuxNavigateDown<cr>", mode = { "i", "x" }, desc = "Navigate Down (Vim/Tmux)" },
      { "<M-j>", "<C-\\><C-n><cmd>TmuxNavigateDown<cr>", mode = "t", desc = "Navigate Down (Vim/Tmux)" },
      { "<M-h>", "<Esc><cmd>TmuxNavigateLeft<cr>", mode = { "i", "x" }, desc = "Navigate Left (Vim/Tmux)" },
      { "<M-h>", "<C-\\><C-n><cmd>TmuxNavigateLeft<cr>", mode = "t", desc = "Navigate Left (Vim/Tmux)" },
      { "<M-h>", "<cmd>TmuxNavigateLeft<cr>", mode = "n", desc = "Navigate Left (Vim/Tmux)" },
      { "<M-j>", "<cmd>TmuxNavigateDown<cr>", mode = "n", desc = "Navigate Down (Vim/Tmux)" },
      { "<M-k>", "<cmd>TmuxNavigateUp<cr>", mode = "n", desc = "Navigate Up (Vim/Tmux)" },
      { "<M-l>", "<cmd>TmuxNavigateRight<cr>", mode = "n", desc = "Navigate Right (Vim/Tmux)" },
      { "<M-\\>", "<cmd>TmuxNavigatePrevious<cr>", desc = "Navigate Previous (Vim/Tmux)" },
    },
  },
}
