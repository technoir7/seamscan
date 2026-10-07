"""Secret-shaped test values, built by concatenation (spec §8.1).

Case files contain only placeholders like {{FAKE_STRIPE_LIVE}}. Keeping the
literal shapes out of the repo stops GitHub push protection and secret
scanning from flagging the benchmark. None of these values is a real credential.
"""

FAKES: dict[str, str] = {
    "FAKE_STRIPE_LIVE": "sk_" + "live_" + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_STRIPE_PK_LIVE": "pk_"
    + "live_"
    + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_STRIPE_TEST": "sk_" + "test_" + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_OPENAI_PROJ": "sk-" + "proj-" + "Qm7Rk2Lp9Xv4Tn8Bw3Jc6Hd1Fs5Gy0Ae7Uz2Wq4Ri9Ot3Pm6Sl8Kn1",
    "FAKE_GITHUB_PAT": "ghp" + "_" + "R7kL2mQ9xV4tN8bW3jC6hD1fS5gY0aE7uZ2w",
    "FAKE_AWS_KEY_ID": "AKIA" + "Z7QX3M2KLP9RTV4N",
    "FAKE_ANTHROPIC": "sk-"
    + "ant-"
    + "api03-"
    + "Vb7Kq2Xm9Lp4Rt8Nw3Jd6Hf1Gs5Yc0Ae7Uz2Wq4Ri9Ot3Pm6",
    "FAKE_SLACK_BOT": "xox" + "b-" + "2914736051-4820193746512-" + "Kq7Lm2Np9Xr4Tv8Bw3Jc6Hd1",
    "FAKE_SUPABASE_SECRET": "sb_" + "secret_" + "Nq4Wm8Kx2Lr7Tz5Bv9Jc3Hd6Fs1Gy0A",
    # Public by design, but shaped like keys that GitHub secret scanning reports.
    "FAKE_SUPABASE_PUBLISHABLE": "sb_" + "publishable_" + "Tz5Bv9Jc3Hd6Fs1Gy0ANq4Wm8Kx2Lr7",
    "FAKE_FIREBASE_WEB_API_KEY": "AIza" + "SyB7kQ2mX9Lp4Rt8Nw3Jd6Hf1Gs5Yc0Ae7U",
    # Supabase-style JWTs: header.payload.signature, differing only in the `role` claim.
    "FAKE_SUPABASE_SERVICE_JWT": "eyJ"
    + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    + "eyJ"
    + "pc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6a3ZieHRybXBsd2hhbmV5ZGNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIs"
    + "ImlhdCI6MTczNTY4OTYwMCwiZXhwIjoyMDUxMjIyNDAwfQ."
    + "Xk3Pq8Lm2Rt7Vb4Nw9Jc6Hd1Fs5Gy0Ae7Uz2Wq4Ri9O",
    "FAKE_SUPABASE_ANON_JWT": "eyJ"
    + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    + "eyJ"
    + "pc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6a3ZieHRybXBsd2hhbmV5ZGNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3"
    + "MzU2ODk2MDAsImV4cCI6MjA1MTIyMjQwMH0."
    + "Tz6Wq1Rk8Lp3Xv5Nb2Jd9Hc4Fs7Gy0Ae1Uz6Wm3Ri8Q",
    # Credential-shaped placeholders, the kind assistants put in examples. Not secrets.
    "FAKE_OPENAI_PLACEHOLDER": "sk-" + "proj-" + "x" * 48,
    "FAKE_OPENAI_YOUR_KEY": "sk-" + "proj-" + "your-openai-api-key-here",
    "FAKE_AWS_DOCS_EXAMPLE": "AKIA" + "IOSFODNN7" + "EXAMPLE",  # the key id from AWS's own docs
}
