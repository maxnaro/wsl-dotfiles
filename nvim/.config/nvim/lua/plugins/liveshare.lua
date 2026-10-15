return {
  {
    "folke/which-key.nvim",
    optional = true,
    opts = {
      spec = {
        { "<leader>l", group = "live share" },
        { "<leader>cl", group = "live share" },
      },
    },
  },
  {
    "azratul/live-share.nvim",
    lazy = false,
    config = function()
      require("live-share.provider").register("tailscale", {
        command = function(_, port, service_url)
          local tailscale_ip = vim.fn.systemlist({ "tailscale", "ip", "-4" })[1]
          if vim.v.shell_error ~= 0 or not tailscale_ip or not tailscale_ip:match("^%d+%.%d+%.%d+%.%d+$") then
            vim.notify("Live Share: could not find an active Tailscale IPv4 address", vim.log.levels.ERROR)
            return ""
          end

          return string.format(
            "printf 'tcp://%s:%d\\n' > %s; sleep infinity",
            tailscale_ip,
            port,
            vim.fn.shellescape(service_url)
          )
        end,
        pattern = "tcp://[%w._-]+:%d+",
      })

      require("live-share").setup({
        username = vim.env.USER or "maxnaro",
        ip_local = "0.0.0.0",
        service = "tailscale",
        port_internal = 8765,
      })
    end,
    keys = {
      { "<leader>lh", "<cmd>LiveShareHostStart<CR>", desc = "Host Live Share" },
      { "<leader>lj", ":LiveShareJoin ", desc = "Join Live Share" },
      { "<leader>ls", "<cmd>LiveShareStop<CR>", desc = "Stop Live Share" },
      { "<leader>lw", "<cmd>LiveShareWorkspace<CR>", desc = "Browse shared workspace" },
      { "<leader>clh", "<cmd>LiveShareHostStart<CR>", desc = "Host Live Share" },
      { "<leader>clj", ":LiveShareJoin ", desc = "Join Live Share" },
      { "<leader>cls", "<cmd>LiveShareStop<CR>", desc = "Stop Live Share" },
      { "<leader>clw", "<cmd>LiveShareWorkspace<CR>", desc = "Browse shared workspace" },
    },
  },
}
