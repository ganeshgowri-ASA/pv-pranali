"""Landing page generator — writes Next.js + Tailwind template files."""
from __future__ import annotations

from pathlib import Path

_LANDING_DIR = Path(__file__).parent / "landing"


def generate_landing_page(
    product_name: str,
    tagline: str = "",
    output_dir: str | None = None,
) -> dict[str, str]:
    """Write a minimal Next.js + Tailwind landing page for the product.

    Args:
        product_name: Display name of the product.
        tagline: Short marketing tagline shown on the hero section.
        output_dir: Where to write files. Defaults to agents/marketing/landing/.

    Returns:
        Dict mapping filename -> absolute path for each written file.
    """
    dest = Path(output_dir) if output_dir else _LANDING_DIR
    dest.mkdir(parents=True, exist_ok=True)

    tagline = tagline or "Precision PV testing, built in India."

    files = {
        "index.tsx": _index_tsx(product_name, tagline),
        "tailwind.config.js": _tailwind_config(),
        "package.json": _package_json(product_name),
        "next.config.js": _next_config(),
    }

    written: dict[str, str] = {}
    for filename, content in files.items():
        path = dest / filename
        path.write_text(content, encoding="utf-8")
        written[filename] = str(path)

    return written


def _index_tsx(product_name: str, tagline: str) -> str:
    return f"""import type {{ NextPage }} from 'next';
import Head from 'next/head';

const Home: NextPage = () => (
  <>
    <Head>
      <title>{product_name} — PV Test Equipment</title>
      <meta name="description" content="{tagline}" />
    </Head>
    <main className="min-h-screen bg-white text-gray-900 font-sans">
      {{/* Hero */}}
      <section className="flex flex-col items-center justify-center px-6 py-24 bg-gradient-to-br from-yellow-50 to-orange-100 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight text-orange-600 mb-4">
          {product_name}
        </h1>
        <p className="text-xl text-gray-700 max-w-2xl">{tagline}</p>
        <a
          href="#contact"
          className="mt-8 inline-block px-8 py-3 bg-orange-500 text-white rounded-xl text-lg font-semibold hover:bg-orange-600 transition"
        >
          Request a Quote
        </a>
      </section>

      {{/* Features */}}
      <section className="py-16 px-6 max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-10">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {{[            {{ title: 'IEC Compliant', desc: 'Meets IEC 61215 and IEC 61853 standards.' }},
            {{ title: 'India-Sourced', desc: 'BoM from Mouser / DigiKey / Robu India stock.' }},
            {{ title: 'Open Architecture', desc: 'MCP + LangGraph pipeline, fully auditable.' }},
          ].map((f) => (
            <div key={{f.title}} className="p-6 rounded-2xl border border-gray-200 shadow-sm">
              <h3 className="text-xl font-semibold mb-2 text-orange-500">{{f.title}}</h3>
              <p className="text-gray-600">{{f.desc}}</p>
            </div>
          ))}}
        </div>
      </section>

      {{/* Contact */}}
      <section id="contact" className="py-16 px-6 bg-gray-50 text-center">
        <h2 className="text-3xl font-bold mb-4">Get in Touch</h2>
        <p className="text-gray-600 mb-6">Ready to upgrade your PV test setup? Drop us a line.</p>
        <a
          href="mailto:ganeshgowri@example.com"
          className="inline-block px-8 py-3 bg-orange-500 text-white rounded-xl text-lg font-semibold hover:bg-orange-600 transition"
        >
          Contact Us
        </a>
      </section>
    </main>
  </>
);

export default Home;
"""


def _tailwind_config() -> str:
    return """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#fff7ed',
          500: '#f97316',
          600: '#ea580c',
        },
      },
    },
  },
  plugins: [],
};
"""


def _package_json(product_name: str) -> str:
    slug = product_name.lower().replace(" ", "-")
    return f"""{{
  "name": "{slug}-landing",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }},
  "devDependencies": {{
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "autoprefixer": "^10.0.0",
    "postcss": "^8.0.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0"
  }}
}}
"""


def _next_config() -> str:
    return """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
"""
