return {
  {
    "folke/which-key.nvim",
    optional = true,
    opts = {
      spec = {
        { "<leader>cl", group = "live share" },
      },
    },
  },
  {
    "azratul/live-share.nvim",
    lazy = false,
    config = function()
      require("live-share").setup({ username = "maxnaro", port_internal = 8765 })
    end,
    keys = {
      { "<leader>clh", "<cmd>LiveShareHostStart<CR>", desc = "Host Live Share" },
      { "<leader>clj", ":LiveShareJoin ", desc = "Join Live Share" },
      { "<leader>cls", "<cmd>LiveShareStop<CR>", desc = "Stop Live Share" },
      { "<leader>clw", "<cmd>LiveShareWorkspace<CR>", desc = "Browse shared workspace" },
    },
  },
}
