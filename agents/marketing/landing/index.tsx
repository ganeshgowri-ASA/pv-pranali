import type { NextPage } from 'next';
import Head from 'next/head';

const Home: NextPage = () => (
  <>
    <Head>
      <title>EL Tester — PV Test Equipment</title>
      <meta name="description" content="Precision PV testing, built in India." />
    </Head>
    <main className="min-h-screen bg-white text-gray-900 font-sans">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-6 py-24 bg-gradient-to-br from-yellow-50 to-orange-100 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight text-orange-600 mb-4">
          EL Tester
        </h1>
        <p className="text-xl text-gray-700 max-w-2xl">Precision PV testing, built in India.</p>
        <a
          href="#contact"
          className="mt-8 inline-block px-8 py-3 bg-orange-500 text-white rounded-xl text-lg font-semibold hover:bg-orange-600 transition"
        >
          Request a Quote
        </a>
      </section>

      {/* Features */}
      <section className="py-16 px-6 max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-10">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { title: 'IEC Compliant', desc: 'Meets IEC 61215 and IEC 61853 standards.' },
            { title: 'India-Sourced', desc: 'BoM from Mouser / DigiKey / Robu India stock.' },
            { title: 'Open Architecture', desc: 'MCP + LangGraph pipeline, fully auditable.' },
          ].map((f) => (
            <div key={f.title} className="p-6 rounded-2xl border border-gray-200 shadow-sm">
              <h3 className="text-xl font-semibold mb-2 text-orange-500">{f.title}</h3>
              <p className="text-gray-600">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Contact */}
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
