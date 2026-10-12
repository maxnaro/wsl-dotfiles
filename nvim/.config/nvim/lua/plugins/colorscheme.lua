return {
  {
    "qaptoR-nvim/chocolatier.nvim",
    lazy = false,
    priority = 1000,
    dependencies = { "rktjmp/lush.nvim" },
    config = function()
      require("chocolatier").setup({
        transparent_mode = true,
      })
      vim.cmd([[colorscheme chocolatier]])
    end,
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "chocolatier",
    },
  },
}
