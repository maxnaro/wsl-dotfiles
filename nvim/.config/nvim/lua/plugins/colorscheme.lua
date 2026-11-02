return {
  {
    "qaptoR-nvim/chocolatier.nvim",
    lazy = false,
    priority = 1000,
    dependencies = { "rktjmp/lush.nvim" },
    config = function()
      require("chocolatier").setup({
        transparent_mode = true,
        overrides = {
          StatusLine = { fg = "#D3C6AA", bg = "NONE" },
          StatusLineNC = { fg = "#a0a8b7", bg = "NONE" },
          FloatBorder = { fg = "#7EA69F", bg = "NONE" },
          LazyGitBorder = { fg = "#7EA69F", bg = "NONE" },
          LazyGitFloat = { fg = "#D3C6AA", bg = "NONE" },
        },
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
