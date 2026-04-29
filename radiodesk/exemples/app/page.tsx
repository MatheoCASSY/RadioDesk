import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <div className="fluff-landing min-h-screen relative font-sans">
      <div className="absolute inset-0 -z-10">
        <Image
          src="/chartegraphique/FluffRadio-CharteGraphique-Noka-x-Pawl/FluffRadio-CG-Full/LivreePNG-FluffRadio-Communication-Livery/FluffRadio-color-background-livery.png"
          alt="background"
          fill
          className="object-cover opacity-85"
          priority
        />
      </div>

      <main className="max-w-6xl mx-auto px-6 py-20 flex flex-col lg:flex-row items-center gap-12">
        <section className="flex-1 fluff-landing-hero">
          <h1 className="text-4xl lg:text-5xl font-extrabold leading-tight">Fluff Radio - l&apos;univers doux et vibrant</h1>
          <p className="mt-6 text-lg max-w-xl">
            Bienvenue sur le panneau d&apos;administration. Gérez les musiques, uploadez de nouveaux titres et
            pilotez la programmation de votre station en toute simplicité.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-4">
            <Link href="/login" className="inline-flex items-center justify-center btn-fluff">Se connecter</Link>
            <Link href="/dashboard" className="inline-flex items-center justify-center btn-outline-fluff">Aller au dashboard</Link>
          </div>

          <div className="mt-8 text-sm fluff-landing-note">Crédits: Fluff Radio - Charte graphique fournie</div>
        </section>

        <aside className="w-full lg:w-1/3">
          <div className="fluff-landing-card rounded-2xl p-6">
            <h4 className="font-semibold mb-3">Aperçu</h4>
            <Image src="/chartegraphique/FluffRadio-CharteGraphique-Noka-x-Pawl/FluffRadio-CG-Full/LivreePNG-FluffRadio-Communication-Livery/FluffRadio-icon-livery.png" alt="icon" width={240} height={240} className="mx-auto" />
          </div>
        </aside>
      </main>

      <footer className="max-w-6xl mx-auto px-6 py-8 text-center text-sm fluff-landing-note">
        © {new Date().getFullYear()} Fluff Radio — Tous droits réservés
      </footer>
    </div>
  );
}
