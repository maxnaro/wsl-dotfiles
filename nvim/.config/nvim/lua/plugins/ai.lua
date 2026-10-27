return {
  {
    "zbirenbaum/copilot.lua",
    -- Sign in explicitly with :Copilot auth, including on a fresh installation.
    build = false,
    init = function()
      -- Blink uses a floating menu, which Copilot's pumvisible check cannot see.
      vim.api.nvim_create_autocmd("User", {
        group = vim.api.nvim_create_augroup("copilot_blink_menu", { clear = true }),
        pattern = { "BlinkCmpMenuOpen", "BlinkCmpMenuClose" },
        callback = function(event)
          vim.b.copilot_suggestion_hidden = event.match == "BlinkCmpMenuOpen"
        end,
      })
    end,
    opts = {
      suggestion = { hide_during_completion = true },
    },
    keys = {
      { "<leader>au", "<cmd>Copilot toggle<cr>", desc = "Toggle Copilot (buffer)" },
    },
  },
  {
    "folke/sidekick.nvim",
    lazy = true,
    cmd = "Sidekick",
    opts = {
      -- Copilot owns inline suggestions; Sidekick is used for CLI sessions.
      nes = { enabled = false },
      copilot = { status = { enabled = false } },
      cli = {
        mux = {
          backend = "tmux",
          enabled = vim.fn.executable("tmux") == 1,
        },
      },
    },
    keys = {
      { "<leader>a", "", desc = "+ai", mode = { "n", "x" } },
      {
        "<leader>as",
        function()
          require("sidekick.cli").select({ filter = { installed = true } })
        end,
        desc = "Select AI Assistant",
      },
      {
        "<leader>aa",
        function()
          require("sidekick.cli").toggle({ filter = { installed = true } })
        end,
        desc = "Toggle AI Assistant",
      },
      {
        "<leader>ac",
        function()
          require("sidekick.cli").toggle({ name = "codex", filter = { installed = true } })
        end,
        desc = "Toggle Codex",
      },
      {
        "<leader>aC",
        function()
          require("sidekick.cli").toggle({ name = "claude", filter = { installed = true } })
        end,
        desc = "Toggle Claude Code",
      },
      {
        "<leader>af",
        function()
          require("sidekick.cli").send({ msg = "{file}", filter = { installed = true } })
        end,
        desc = "Send File to AI Assistant",
      },
      {
        "<leader>av",
        function()
          require("sidekick.cli").send({ msg = "{selection}", filter = { installed = true } })
        end,
        mode = { "x" },
        desc = "Send Selection to AI Assistant",
      },
    },
  },
}
