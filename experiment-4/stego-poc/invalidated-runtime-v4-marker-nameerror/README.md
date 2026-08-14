# Invalidated runtime v4 marker-server smoke

The explicit positive smoke control appended `amber`, then raised `NameError`
on a leftover `os.chmod` call after the timestamp-removal edit. Codex retried,
creating two local entries. No experimental prompt ran. The fixed server simply
opens its constant path in the mode-700 tmpfs, appends one `{"label": ...}`
object, and returns success.
