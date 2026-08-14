# Runtime artifact note

Every frozen trace contains one identical startup `item.completed` event of type `error` stating that Code Mode is unavailable because its host was disabled and that it failed closed. This was an expected consequence of the preregistered no-tool configuration, which explicitly disabled both Code Mode and its host.

The traces contain no observable command, MCP, browser, computer, file-change, web-search, image-generation, or other tool-invocation item. All subjects exited successfully and produced a final message. The startup item was preserved rather than hidden, and no trial was retried because of it.

