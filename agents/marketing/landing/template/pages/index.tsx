import type { NextPage, GetStaticProps } from "next";
import Head from "next/head";
import path from "path";
import fs from "fs";

interface Product {
  product_name: string;
  tagline: string;
  features: string[];
  cta_url: string;
  contact_email: string;
}

interface Props {
  product: Product;
}

const Home: NextPage<Props> = ({ product }) => {
  return (
    <>
      <Head>
        <title>{product.product_name}</title>
        <meta name="description" content={product.tagline} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-white flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 px-6 py-4">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <span className="text-xl font-bold text-gray-900">
              {product.product_name}
            </span>
            <a
              href={`mailto:${product.contact_email}`}
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              {product.contact_email}
            </a>
          </div>
        </header>

        {/* Hero */}
        <main className="flex-1">
          <section className="bg-gradient-to-br from-indigo-50 to-white px-6 py-20 sm:py-32">
            <div className="max-w-5xl mx-auto text-center">
              <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight">
                {product.product_name}
              </h1>
              <p className="mt-6 text-xl sm:text-2xl text-gray-600 max-w-2xl mx-auto">
                {product.tagline}
              </p>
              <div className="mt-10">
                <a
                  href={product.cta_url}
                  className="inline-block bg-indigo-600 text-white text-lg font-semibold px-8 py-4 rounded-xl shadow hover:bg-indigo-700 active:bg-indigo-800 transition-colors"
                >
                  Get Started
                </a>
              </div>
            </div>
          </section>

          {/* Features */}
          <section className="px-6 py-16 sm:py-24">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
                Key Features
              </h2>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {product.features.map((feature, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-4 bg-gray-50 rounded-xl p-6"
                  >
                    <span className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-bold text-sm">
                      {index + 1}
                    </span>
                    <span className="text-gray-700 text-base leading-relaxed">
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* CTA Banner */}
          <section className="bg-indigo-600 px-6 py-16">
            <div className="max-w-5xl mx-auto text-center">
              <h2 className="text-2xl sm:text-3xl font-bold text-white mb-6">
                Ready to get started?
              </h2>
              <a
                href={product.cta_url}
                className="inline-block bg-white text-indigo-600 text-lg font-semibold px-8 py-4 rounded-xl shadow hover:bg-indigo-50 transition-colors"
              >
                Start Now
              </a>
            </div>
          </section>
        </main>

        {/* Footer */}
        <footer className="bg-gray-900 text-gray-400 px-6 py-8">
          <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm">
            <span>&copy; {new Date().getFullYear()} {product.product_name}. All rights reserved.</span>
            <a
              href={`mailto:${product.contact_email}`}
              className="hover:text-white transition-colors"
            >
              {product.contact_email}
            </a>
          </div>
        </footer>
      </div>
    </>
  );
};

export const getStaticProps: GetStaticProps<Props> = async () => {
  const filePath = path.join(process.cwd(), "product.json");
  const raw = fs.readFileSync(filePath, "utf-8");
  const product: Product = JSON.parse(raw);
  return { props: { product } };
};

export default Home;
