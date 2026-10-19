return {
  {
    "iamcco/markdown-preview.nvim",
    init = function()
      if vim.fn.has("wsl") ~= 1 then
        return
      end

      -- Windows executables are not always included in WSL's PATH.
      local cmd = vim.fn.exepath("cmd.exe")
      if cmd == "" then
        cmd = "/mnt/c/Windows/System32/cmd.exe"
      end

      vim.g.mkdp_browserfunc = "OpenMarkdownPreview"
      vim.cmd([[
        function! OpenMarkdownPreview(url) abort
          call v:lua.OpenMarkdownPreview(a:url)
        endfunction
      ]])
      _G.OpenMarkdownPreview = function(url)
        local job = vim.fn.jobstart({ cmd, "/c", "start", '""', url:gsub("&", "^&") }, {
          -- Avoid cmd.exe's warning about Linux/UNC working directories.
          cwd = "/mnt/c",
          detach = true,
        })
        if job <= 0 then
          vim.notify("Could not open Markdown preview: " .. url, vim.log.levels.ERROR)
        end
      end
    end,
  },
}
