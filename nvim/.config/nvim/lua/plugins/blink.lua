return {
  {
    "saghen/blink.cmp",
    opts = function(_, opts)
      opts.keymap = opts.keymap or {}
      opts.keymap.preset = "super-tab"
      opts.keymap["<Tab>"] = {
        function(cmp)
          if cmp.is_menu_visible() then
            return cmp.select_and_accept()
          end
        end,
        "snippet_forward",
        LazyVim.cmp.map({ "ai_accept" }),
        "fallback",
      }
      opts.keymap["<S-Tab>"] = { "select_prev", "snippet_backward", "fallback" }
    end,
  },
}
