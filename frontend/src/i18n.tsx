import { createContext, useContext, useState, type ReactNode } from "react";

export type Lang = "en" | "ro" | "es" | "de" | "fr";
export const LANGS: { id: Lang; label: string; flag: string }[] = [
  { id: "en", label: "English", flag: "🇬🇧" },
  { id: "ro", label: "Română", flag: "🇷🇴" },
  { id: "es", label: "Español", flag: "🇪🇸" },
  { id: "de", label: "Deutsch", flag: "🇩🇪" },
  { id: "fr", label: "Français", flag: "🇫🇷" },
];

type Dict = Record<string, string>;

const en: Dict = {
  "tab.library": "Library",
  "reset": "Start over",
  "reset.hint": "Clear the last sort from this screen. Files on disk are not touched.",
  "tab.statistics": "Statistics",
  "tagline": "photos & videos, sorted",
  "tab.sort": "Sort", "tab.review": "Review", "tab.categories": "Categories", "tab.history": "History", "tab.settings": "Settings",
  "hero.before": "Sorting my", "hero.after": "folder", "hero.change": "Choose another folder",
  "hero.sorted_into": "sorted folders directly inside",
  "sort": "Sort", "sort.again": "Sort again", "stop": "Stop",
  "hint.idle": "Nothing is moved until you press Apply",
  "status.idle": "Ready when you are", "status.scanning": "Looking for photos & videos…",
  "status.analyzing": "Looking at {n} / {total}…", "status.dedupe": "Finding duplicates…",
  "status.checking": "Checking sharpness, eyes & smiles…", "status.reading": "Reading text in photos…",
  "status.faces": "Recognizing people…", "status.ai": "Asking AI…", "status.sorting": "Sorting into folders…",
  "status.done": "Sorted, nothing moved yet. Review & apply", "status.applied": "Applied ✓",
  "status.undone": "Undone, all files are back", "status.stopped": "Stopped", "status.error": "Something went wrong",
  "stats.total": "Total files", "stats.videos": "Videos", "stats.photos": "Photos", "stats.folders": "Folders created",
  "stats.duplicates": "Duplicates found",
  "col.photos": "Photos", "col.videos": "Videos", "col.novideos": "No videos in this folder.",
  "apply.summary": "{n} files planned into {folders} folders.", "apply.dups": "{n} duplicates set aside.",
  "apply.untouched": "Nothing has been touched yet.", "apply.move": "Apply · move files", "apply.copy": "Apply · copy files",
  "apply.applying": "Applying…", "rerun": "Re-run", "undo": "Undo", "apply.done": "Done. Your files are in {path}.",
  "apply.undone": "Undone. Every file is back where it was.",
  "caption.idle": "a total mess", "caption.sorted": "a total mess, sorted", "caption.applied": "…not anymore",
  "caption.empty": "nothing to sort here", "caption.error": "oops", "caption.paused": "paused",
  "recipe.ask": "What's in this folder?", "recipe.recommended": "Recommended", "recipe.more": "Show all options",
  "recipe.less": "Fewer options", "recipe.looking": "Looking at a few photos to suggest the best way…",
  "recipe.counts": "{photos} photos · {videos} videos",
  "reason.theme": "Looks like {theme} ({pct}% sure)", "reason.shoot": "A {theme} shoot: pick the keepers",
  "reason.people": "{pct}% of the photos show people", "reason.text": "{pct}% look like screenshots or documents",
  "reason.discover": "Let the app find the groups", "reason.no_photos": "Only videos here",
  "r.camera-roll.t": "Camera roll / Downloads", "r.camera-roll.d": "Selfies, food, travel, screenshots… everyday folders",
  "r.photoshoot.t": "Cull a photoshoot", "r.photoshoot.d": "Keepers, picks ★, blurry, eyes closed, best of bursts",
  "r.wedding.t": "A wedding", "r.wedding.d": "Getting ready, ceremony, couple, family, party",
  "r.boudoir.t": "Boudoir / glamour", "r.boudoir.d": "Lingerie studio & bedroom, on the bed, corset, B&W, details",
  "r.portraits.t": "Portraits & outfits", "r.portraits.d": "Headshots, full-body looks, dresses, details, scenery",
  "r.people.t": "By person", "r.people.d": "One folder per person, recognized by face",
  "r.travel.t": "A trip", "r.travel.d": "Beaches, mountains, cities, food, hotels, night life",
  "r.documents.t": "Screenshots & documents", "r.documents.d": "Receipts, IDs, notes, slides; reads the text (OCR)",
  "r.discover.t": "Not sure: discover", "r.discover.d": "Finds the groups itself and names them",
  "r.by-date.t": "By date", "r.by-date.d": "2025/07 - July folders from the photo date",
  "quick.title": "Quick settings", "quick.saved": "Saved automatically · applies to the next Sort", "quick.all": "All settings →",
  "lang": "Language", "rename": "Rename folder", "rename.ok": "Renamed",
  "review.search": "Search file name, folder or text in the photo",
  "footer": "runs locally · nothing is moved until you press Apply",
};

const ro: Dict = {
  "tab.library": "Bibliotecă",
  "reset": "Ia-o de la capăt",
  "reset.hint": "Șterge ultima sortare de pe ecran. Fișierele de pe disc nu sunt atinse.",
  "tab.statistics": "Statistici",
  "tagline": "poze și video, sortate",
  "tab.sort": "Sortare", "tab.review": "Verificare", "tab.categories": "Categorii", "tab.history": "Istoric", "tab.settings": "Setări",
  "hero.before": "Sortez folderul", "hero.after": "", "hero.change": "Alege alt folder",
  "hero.sorted_into": "folderele sortate direct înăuntru",
  "sort": "Sortează", "sort.again": "Sortează din nou", "stop": "Oprește",
  "hint.idle": "Nimic nu se mută până nu apeși Aplică",
  "status.idle": "Gata când ești gata", "status.scanning": "Caut poze și video…", "status.analyzing": "Analizez {n} / {total}…",
  "status.dedupe": "Caut duplicate…", "status.checking": "Verific claritatea, ochii și zâmbetele…",
  "status.reading": "Citesc textul din poze…", "status.faces": "Recunosc persoanele…", "status.ai": "Întreb AI…",
  "status.sorting": "Sortez în foldere…", "status.done": "Sortat, nimic mutat încă. Verifică și aplică",
  "status.applied": "Aplicat ✓", "status.undone": "Anulat, toate fișierele sunt la loc", "status.stopped": "Oprit",
  "status.error": "Ceva n-a mers",
  "stats.total": "Fișiere", "stats.videos": "Video", "stats.photos": "Poze", "stats.folders": "Foldere create",
  "stats.duplicates": "Duplicate găsite",
  "col.photos": "Poze", "col.videos": "Video", "col.novideos": "Niciun video în acest folder.",
  "apply.summary": "{n} fișiere planificate în {folders} foldere.", "apply.dups": "{n} duplicate puse deoparte.",
  "apply.untouched": "Nimic n-a fost atins încă.", "apply.move": "Aplică · mută fișierele", "apply.copy": "Aplică · copiază fișierele",
  "apply.applying": "Aplic…", "rerun": "Din nou", "undo": "Anulează", "apply.done": "Gata. Fișierele sunt în {path}.",
  "apply.undone": "Anulat. Fiecare fișier e înapoi la locul lui.",
  "caption.idle": "un haos total", "caption.sorted": "un haos total, sortat", "caption.applied": "…nu mai e",
  "caption.empty": "nimic de sortat aici", "caption.error": "ups", "caption.paused": "pe pauză",
  "recipe.ask": "Ce e în acest folder?", "recipe.recommended": "Recomandat", "recipe.more": "Toate opțiunile",
  "recipe.less": "Mai puține opțiuni", "recipe.looking": "Mă uit la câteva poze ca să-ți sugerez cel mai bun mod…",
  "recipe.counts": "{photos} poze · {videos} video",
  "reason.theme": "Pare a fi {theme} ({pct}% sigur)", "reason.shoot": "O ședință {theme}: alege cele mai bune",
  "reason.people": "{pct}% dintre poze au oameni", "reason.text": "{pct}% par capturi de ecran sau documente",
  "reason.discover": "Lasă aplicația să găsească grupurile", "reason.no_photos": "Aici sunt doar video",
  "r.camera-roll.t": "Galerie telefon / Descărcări", "r.camera-roll.d": "Selfie-uri, mâncare, călătorii, capturi… foldere de zi cu zi",
  "r.photoshoot.t": "Selecție ședință foto", "r.photoshoot.d": "Păstrate, favorite ★, neclare, ochi închiși, cele mai bune din rafale",
  "r.wedding.t": "O nuntă", "r.wedding.d": "Pregătiri, ceremonie, cuplu, familie, petrecere",
  "r.boudoir.t": "Boudoir / glamour", "r.boudoir.d": "Lenjerie în studio și dormitor, pe pat, corset, alb-negru, detalii",
  "r.portraits.t": "Portrete și ținute", "r.portraits.d": "Portrete, ținute complete, rochii, detalii, peisaj",
  "r.people.t": "După persoană", "r.people.d": "Un folder pentru fiecare persoană, recunoscută după față",
  "r.travel.t": "O călătorie", "r.travel.d": "Plaje, munți, orașe, mâncare, hoteluri, viață de noapte",
  "r.documents.t": "Capturi și documente", "r.documents.d": "Bonuri, acte, notițe, slide-uri; citește textul (OCR)",
  "r.discover.t": "Nu știu: descoperă", "r.discover.d": "Găsește singur grupurile și le denumește",
  "r.by-date.t": "După dată", "r.by-date.d": "Foldere 2025/07 - Iulie după data pozei",
  "quick.title": "Setări rapide", "quick.saved": "Salvate automat · se aplică la următoarea sortare", "quick.all": "Toate setările →",
  "lang": "Limbă", "rename": "Redenumește folderul", "rename.ok": "Redenumit",
  "review.search": "Caută nume, folder sau text din poză",
  "footer": "rulează local · nimic nu se mută până nu apeși Aplică",
};

const es: Dict = {
  "tab.library": "Biblioteca",
  "reset": "Empezar de cero",
  "reset.hint": "Quita la última ordenación de la pantalla. No toca los archivos.",
  "tab.statistics": "Estadísticas",
  "tagline": "fotos y vídeos, ordenados",
  "tab.sort": "Ordenar", "tab.review": "Revisar", "tab.categories": "Categorías", "tab.history": "Historial", "tab.settings": "Ajustes",
  "hero.before": "Ordenando mi carpeta", "hero.after": "", "hero.change": "Elegir otra carpeta",
  "hero.sorted_into": "carpetas ordenadas directamente dentro",
  "sort": "Ordenar", "sort.again": "Ordenar otra vez", "stop": "Detener",
  "hint.idle": "No se mueve nada hasta que pulses Aplicar",
  "status.idle": "Listo cuando quieras", "status.scanning": "Buscando fotos y vídeos…", "status.analyzing": "Analizando {n} / {total}…",
  "status.dedupe": "Buscando duplicados…", "status.checking": "Revisando nitidez, ojos y sonrisas…",
  "status.reading": "Leyendo texto en las fotos…", "status.faces": "Reconociendo personas…", "status.ai": "Preguntando a la IA…",
  "status.sorting": "Ordenando en carpetas…", "status.done": "Ordenado, nada movido aún. Revisa y aplica",
  "status.applied": "Aplicado ✓", "status.undone": "Deshecho, todo está en su sitio", "status.stopped": "Detenido",
  "status.error": "Algo salió mal",
  "stats.total": "Archivos", "stats.videos": "Vídeos", "stats.photos": "Fotos", "stats.folders": "Carpetas creadas",
  "stats.duplicates": "Duplicados",
  "col.photos": "Fotos", "col.videos": "Vídeos", "col.novideos": "No hay vídeos en esta carpeta.",
  "apply.summary": "{n} archivos planificados en {folders} carpetas.", "apply.dups": "{n} duplicados apartados.",
  "apply.untouched": "Aún no se ha tocado nada.", "apply.move": "Aplicar · mover archivos", "apply.copy": "Aplicar · copiar archivos",
  "apply.applying": "Aplicando…", "rerun": "Repetir", "undo": "Deshacer", "apply.done": "Listo. Tus archivos están en {path}.",
  "apply.undone": "Deshecho. Cada archivo ha vuelto a su sitio.",
  "caption.idle": "un desastre total", "caption.sorted": "un desastre total, ordenado", "caption.applied": "…ya no",
  "caption.empty": "nada que ordenar", "caption.error": "ups", "caption.paused": "en pausa",
  "recipe.ask": "¿Qué hay en esta carpeta?", "recipe.recommended": "Recomendado", "recipe.more": "Ver todas las opciones",
  "recipe.less": "Menos opciones", "recipe.looking": "Mirando algunas fotos para sugerir la mejor forma…",
  "recipe.counts": "{photos} fotos · {videos} vídeos",
  "reason.theme": "Parece {theme} ({pct}% seguro)", "reason.shoot": "Una sesión de {theme}: elige las mejores",
  "reason.people": "{pct}% de las fotos muestran personas", "reason.text": "{pct}% parecen capturas o documentos",
  "reason.discover": "Deja que la app encuentre los grupos", "reason.no_photos": "Aquí solo hay vídeos",
  "r.camera-roll.t": "Galería / Descargas", "r.camera-roll.d": "Selfies, comida, viajes, capturas… carpetas del día a día",
  "r.photoshoot.t": "Seleccionar una sesión", "r.photoshoot.d": "Buenas, favoritas ★, borrosas, ojos cerrados, mejor de ráfaga",
  "r.wedding.t": "Una boda", "r.wedding.d": "Preparativos, ceremonia, pareja, familia, fiesta",
  "r.boudoir.t": "Boudoir / glamour", "r.boudoir.d": "Lencería en estudio y dormitorio, en la cama, corsé, B/N, detalles",
  "r.portraits.t": "Retratos y looks", "r.portraits.d": "Retratos, looks de cuerpo entero, vestidos, detalles, paisaje",
  "r.people.t": "Por persona", "r.people.d": "Una carpeta por persona, reconocida por la cara",
  "r.travel.t": "Un viaje", "r.travel.d": "Playas, montañas, ciudades, comida, hoteles, noche",
  "r.documents.t": "Capturas y documentos", "r.documents.d": "Tickets, documentos, notas, diapositivas; lee el texto (OCR)",
  "r.discover.t": "No lo sé: descubrir", "r.discover.d": "Encuentra los grupos y les pone nombre",
  "r.by-date.t": "Por fecha", "r.by-date.d": "Carpetas 2025/07 - Julio según la fecha",
  "quick.title": "Ajustes rápidos", "quick.saved": "Guardado automáticamente · para el próximo orden", "quick.all": "Todos los ajustes →",
  "lang": "Idioma", "rename": "Renombrar carpeta", "rename.ok": "Renombrada",
  "review.search": "Buscar nombre, carpeta o texto en la foto",
  "footer": "funciona en local · no se mueve nada hasta que pulses Aplicar",
};

const de: Dict = {
  "tab.library": "Bibliothek",
  "reset": "Neu beginnen",
  "reset.hint": "Entfernt die letzte Sortierung vom Bildschirm. Dateien bleiben unberührt.",
  "tab.statistics": "Statistik",
  "tagline": "Fotos & Videos, sortiert",
  "tab.sort": "Sortieren", "tab.review": "Prüfen", "tab.categories": "Kategorien", "tab.history": "Verlauf", "tab.settings": "Einstellungen",
  "hero.before": "Ich sortiere den Ordner", "hero.after": "", "hero.change": "Anderen Ordner wählen",
  "hero.sorted_into": "sortierte Ordner direkt darin",
  "sort": "Sortieren", "sort.again": "Erneut sortieren", "stop": "Stopp",
  "hint.idle": "Nichts wird verschoben, bevor du auf Anwenden drückst",
  "status.idle": "Bereit, wenn du es bist", "status.scanning": "Suche Fotos & Videos…", "status.analyzing": "Analysiere {n} / {total}…",
  "status.dedupe": "Suche Duplikate…", "status.checking": "Prüfe Schärfe, Augen & Lächeln…",
  "status.reading": "Lese Text in Fotos…", "status.faces": "Erkenne Personen…", "status.ai": "Frage die KI…",
  "status.sorting": "Sortiere in Ordner…", "status.done": "Sortiert, noch nichts verschoben. Prüfen & anwenden",
  "status.applied": "Angewendet ✓", "status.undone": "Rückgängig gemacht, alles ist zurück", "status.stopped": "Gestoppt",
  "status.error": "Etwas ist schiefgelaufen",
  "stats.total": "Dateien", "stats.videos": "Videos", "stats.photos": "Fotos", "stats.folders": "Ordner erstellt",
  "stats.duplicates": "Duplikate",
  "col.photos": "Fotos", "col.videos": "Videos", "col.novideos": "Keine Videos in diesem Ordner.",
  "apply.summary": "{n} Dateien in {folders} Ordner geplant.", "apply.dups": "{n} Duplikate beiseitegelegt.",
  "apply.untouched": "Noch wurde nichts verändert.", "apply.move": "Anwenden · verschieben", "apply.copy": "Anwenden · kopieren",
  "apply.applying": "Wende an…", "rerun": "Neu", "undo": "Rückgängig", "apply.done": "Fertig. Deine Dateien sind in {path}.",
  "apply.undone": "Rückgängig gemacht. Jede Datei ist wieder an ihrem Platz.",
  "caption.idle": "ein totales Chaos", "caption.sorted": "ein totales Chaos, sortiert", "caption.applied": "…nicht mehr",
  "caption.empty": "nichts zu sortieren", "caption.error": "hoppla", "caption.paused": "pausiert",
  "recipe.ask": "Was ist in diesem Ordner?", "recipe.recommended": "Empfohlen", "recipe.more": "Alle Optionen zeigen",
  "recipe.less": "Weniger Optionen", "recipe.looking": "Ich schaue mir ein paar Fotos an, um den besten Weg vorzuschlagen…",
  "recipe.counts": "{photos} Fotos · {videos} Videos",
  "reason.theme": "Sieht nach {theme} aus ({pct}% sicher)", "reason.shoot": "Ein {theme}-Shooting: die besten auswählen",
  "reason.people": "{pct}% der Fotos zeigen Menschen", "reason.text": "{pct}% sehen nach Screenshots oder Dokumenten aus",
  "reason.discover": "Lass die App die Gruppen finden", "reason.no_photos": "Hier sind nur Videos",
  "r.camera-roll.t": "Handy-Galerie / Downloads", "r.camera-roll.d": "Selfies, Essen, Reisen, Screenshots… Alltagsordner",
  "r.photoshoot.t": "Shooting aussortieren", "r.photoshoot.d": "Behalten, Favoriten ★, unscharf, Augen zu, beste aus Serien",
  "r.wedding.t": "Eine Hochzeit", "r.wedding.d": "Vorbereitung, Trauung, Paar, Familie, Feier",
  "r.boudoir.t": "Boudoir / Glamour", "r.boudoir.d": "Dessous im Studio & Schlafzimmer, auf dem Bett, Korsett, S/W, Details",
  "r.portraits.t": "Porträts & Outfits", "r.portraits.d": "Porträts, Ganzkörper-Looks, Kleider, Details, Landschaft",
  "r.people.t": "Nach Person", "r.people.d": "Ein Ordner pro Person, am Gesicht erkannt",
  "r.travel.t": "Eine Reise", "r.travel.d": "Strände, Berge, Städte, Essen, Hotels, Nachtleben",
  "r.documents.t": "Screenshots & Dokumente", "r.documents.d": "Belege, Ausweise, Notizen, Folien; liest den Text (OCR)",
  "r.discover.t": "Unsicher: entdecken", "r.discover.d": "Findet die Gruppen selbst und benennt sie",
  "r.by-date.t": "Nach Datum", "r.by-date.d": "Ordner 2025/07 - Juli nach Aufnahmedatum",
  "quick.title": "Schnelleinstellungen", "quick.saved": "Automatisch gespeichert · gilt für die nächste Sortierung", "quick.all": "Alle Einstellungen →",
  "lang": "Sprache", "rename": "Ordner umbenennen", "rename.ok": "Umbenannt",
  "review.search": "Dateiname, Ordner oder Text im Foto suchen",
  "footer": "läuft lokal · nichts wird verschoben, bevor du auf Anwenden drückst",
};

const fr: Dict = {
  "tab.library": "Bibliothèque",
  "reset": "Recommencer",
  "reset.hint": "Efface le dernier tri de l'écran. Les fichiers ne sont pas touchés.",
  "tab.statistics": "Statistiques",
  "tagline": "photos et vidéos, triées",
  "tab.sort": "Trier", "tab.review": "Vérifier", "tab.categories": "Catégories", "tab.history": "Historique", "tab.settings": "Réglages",
  "hero.before": "Je trie le dossier", "hero.after": "", "hero.change": "Choisir un autre dossier",
  "hero.sorted_into": "dossiers triés directement dedans",
  "sort": "Trier", "sort.again": "Trier à nouveau", "stop": "Arrêter",
  "hint.idle": "Rien ne bouge avant que tu appuies sur Appliquer",
  "status.idle": "Prêt quand tu l'es", "status.scanning": "Recherche des photos et vidéos…", "status.analyzing": "Analyse {n} / {total}…",
  "status.dedupe": "Recherche des doublons…", "status.checking": "Vérification de la netteté, des yeux et des sourires…",
  "status.reading": "Lecture du texte dans les photos…", "status.faces": "Reconnaissance des personnes…", "status.ai": "Je demande à l'IA…",
  "status.sorting": "Tri dans les dossiers…", "status.done": "Trié, rien n'a bougé. Vérifie et applique",
  "status.applied": "Appliqué ✓", "status.undone": "Annulé, tout est revenu", "status.stopped": "Arrêté",
  "status.error": "Un problème est survenu",
  "stats.total": "Fichiers", "stats.videos": "Vidéos", "stats.photos": "Photos", "stats.folders": "Dossiers créés",
  "stats.duplicates": "Doublons",
  "col.photos": "Photos", "col.videos": "Vidéos", "col.novideos": "Aucune vidéo dans ce dossier.",
  "apply.summary": "{n} fichiers prévus dans {folders} dossiers.", "apply.dups": "{n} doublons mis de côté.",
  "apply.untouched": "Rien n'a encore été touché.", "apply.move": "Appliquer · déplacer", "apply.copy": "Appliquer · copier",
  "apply.applying": "Application…", "rerun": "Relancer", "undo": "Annuler", "apply.done": "Terminé. Tes fichiers sont dans {path}.",
  "apply.undone": "Annulé. Chaque fichier est revenu à sa place.",
  "caption.idle": "un vrai bazar", "caption.sorted": "un vrai bazar, trié", "caption.applied": "…plus maintenant",
  "caption.empty": "rien à trier ici", "caption.error": "oups", "caption.paused": "en pause",
  "recipe.ask": "Qu'y a-t-il dans ce dossier ?", "recipe.recommended": "Recommandé", "recipe.more": "Voir toutes les options",
  "recipe.less": "Moins d'options", "recipe.looking": "Je regarde quelques photos pour proposer la meilleure méthode…",
  "recipe.counts": "{photos} photos · {videos} vidéos",
  "reason.theme": "Ressemble à {theme} ({pct}% sûr)", "reason.shoot": "Une séance {theme} : garde les meilleures",
  "reason.people": "{pct}% des photos montrent des personnes", "reason.text": "{pct}% ressemblent à des captures ou documents",
  "reason.discover": "Laisse l'app trouver les groupes", "reason.no_photos": "Il n'y a que des vidéos ici",
  "r.camera-roll.t": "Pellicule / Téléchargements", "r.camera-roll.d": "Selfies, repas, voyages, captures… dossiers du quotidien",
  "r.photoshoot.t": "Trier une séance photo", "r.photoshoot.d": "À garder, favorites ★, floues, yeux fermés, meilleure des rafales",
  "r.wedding.t": "Un mariage", "r.wedding.d": "Préparatifs, cérémonie, couple, famille, fête",
  "r.boudoir.t": "Boudoir / glamour", "r.boudoir.d": "Lingerie en studio et chambre, sur le lit, corset, N&B, détails",
  "r.portraits.t": "Portraits et tenues", "r.portraits.d": "Portraits, tenues en pied, robes, détails, paysage",
  "r.people.t": "Par personne", "r.people.d": "Un dossier par personne, reconnue au visage",
  "r.travel.t": "Un voyage", "r.travel.d": "Plages, montagnes, villes, cuisine, hôtels, nuit",
  "r.documents.t": "Captures et documents", "r.documents.d": "Tickets, papiers, notes, diapos ; lit le texte (OCR)",
  "r.discover.t": "Je ne sais pas : découvrir", "r.discover.d": "Trouve les groupes et les nomme",
  "r.by-date.t": "Par date", "r.by-date.d": "Dossiers 2025/07 - Juillet selon la date",
  "quick.title": "Réglages rapides", "quick.saved": "Enregistré automatiquement · pour le prochain tri", "quick.all": "Tous les réglages →",
  "lang": "Langue", "rename": "Renommer le dossier", "rename.ok": "Renommé",
  "review.search": "Chercher un nom, un dossier ou du texte dans la photo",
  "footer": "fonctionne en local · rien ne bouge avant que tu appuies sur Appliquer",
};

import { MORE } from "./i18n-more";
const DICTS: Record<Lang, Dict> = {
  en: { ...en, ...MORE.en }, ro: { ...ro, ...MORE.ro }, es: { ...es, ...MORE.es }, de: { ...de, ...MORE.de }, fr: { ...fr, ...MORE.fr },
};
const KEY = "aio.lang";

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY) as Lang | null;
    if (saved && saved in DICTS) return saved;
  } catch {
    /* storage unavailable */
  }
  const nav = (navigator.language || "en").slice(0, 2) as Lang;
  return nav in DICTS ? nav : "en";
}

export type T = (key: string, vars?: Record<string, string | number>) => string;
const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: T }>({
  lang: "en",
  setLang: () => {},
  t: (k) => en[k] ?? k,
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(KEY, l);
    } catch {
      /* storage unavailable */
    }
    document.documentElement.lang = l;
  };
  const t: T = (key, vars) => {
    let s = DICTS[lang][key] ?? en[key] ?? key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
    return s;
  };
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
