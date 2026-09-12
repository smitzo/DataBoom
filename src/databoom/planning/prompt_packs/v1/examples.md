Example intent: Create a small commerce dataset for integration tests.

Expected behavior: retain every declared resource, choose smaller target counts,
state that parent resources are generated first, and warn if the request does not
specify a time range.

Example intent: Create an account and device graph for fraud-rule testing.

Expected behavior: retain all node and edge resources, generate stable node IDs
before edges, and state that every edge endpoint must reference a generated node.
