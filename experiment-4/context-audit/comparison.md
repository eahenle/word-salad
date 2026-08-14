# Historical versus clean image comparison

Historical frozen image: `sha256:882b506db7abe1d804da2cf4644364ae951accc24f732c04bc7c4ef75b38f254`

Clean reconstructed PoC image: `sha256:bf7dfa417f238e6e0576a9d68ebd1dd16d6246eda4a3ae86015c90d0291b3709`

## Result

The images are logically equivalent for the context-contamination question. All shared regular files except `/etc/shadow` and the runtime-injected `/etc/hostname` are byte-identical. The only path-set differences are npm build-log filenames containing their respective build timestamps.

| Check | Historical | Clean |
| --- | ---: | ---: |
| Filesystem entries | 5672 | 5672 |
| Shared paths | 5670 | 5670 |
| Shared regular files | 4236 | 4236 |
| Byte-identical shared regular files | 4234 | 4234 |
| Project-term hit files | 48 | 48 |

The project-term hit maps are identical. The sole intentional experiment-specific file is `/opt/q4/marker_server.py`, which contains `amber` and `violet`. Generic matches such as `multiplex`, `interleave`, `stride`, and `prompt injection` occur in standard runtime/package binaries; none is a project prompt, history, memory, or instruction file.

## Expected build/runtime differences

- `/etc/hostname`: generated for each diagnostic container.
- `/etc/shadow`: differs because the clean `adduser` build step generated fresh locked-account material.
- `/root/.npm/_logs/*.log`: same two npm operations, timestamped on different build dates.
- Layer count is 14 historical versus 13 clean because the historical 4B.1 child overwrote the 4B marker server in an extra layer; the clean PoC copies the frozen 4B.1 server once.

No unexplained content, configuration, or path difference remains.
