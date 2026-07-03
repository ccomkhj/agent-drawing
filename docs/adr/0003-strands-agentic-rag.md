# The ask path is a Strands agent with tools, not a fixed pipeline

Plain vector RAG is a fixed pipeline (embed question → top-k → one Claude call)
and barely needs an agent framework. We deliberately gave the ask path a **Strands
agent with tools** — `search_documents(query, category?)`, `list_categories()`,
`read_full_pdf(doc_id)` — so Claude decides when to search, can search multiple
times, narrow by Category, or pull a whole Document when chunks are insufficient.
This is what makes Strands (the chosen agentic framework) load-bearing rather than
ceremonial, and it answers multi-step questions the fixed pipeline can't. The cost
is extra latency and tokens per question versus a single call.
