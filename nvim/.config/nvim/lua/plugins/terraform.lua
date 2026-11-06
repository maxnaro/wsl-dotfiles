return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        terraformls = {
          on_attach = function(_, bufnr)
            -- Neovim 0.11 does not provide codelens.enable.
            if vim.lsp.codelens.enable then
              vim.lsp.codelens.enable(true, { bufnr = bufnr })
            end
          end,
        },
      },
    },
  },
}
