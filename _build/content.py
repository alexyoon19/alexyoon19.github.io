"""Everything the site says, in one place. Edit here, then run build_site.py."""

NAME = 'Alex Yoon'
AFFILIATION = 'M.S. candidate in Financial Engineering, Columbia University'
LINKEDIN = 'https://www.linkedin.com/in/alexyoon19'
EMAIL = 'ayoon19@outlook.com'      # shown on the Contact page only
UPDATED = 'November 2026'

NAV = [
    ('index.html', 'About'),
    ('resume.html', 'Résumé'),
    ('research.html', 'Research papers'),
    ('working.html', 'Working papers & blog'),
    ('honors.html', 'Honors and awards'),
    ('contact.html', 'Contact'),
]

BIO = [
    'I am a master’s student in financial engineering at Columbia University. I am currently studying how AI’s physical, energy, and human footprints show in prices, economic growth, and ethical meaning.',
    'Before Columbia, I spent two years in energy &amp; infrastructure investment banking at DC Advisory, where I was part of the first analyst cohort in the NY team. Prior to that, I studied economics, philosophy, and physics at the University of Chicago. There I wrote honors theses in two fields: one with Esteban Rossi-Hansberg on the pricing of renewable energy certificates, and one with Robert Pippin on art as a ground of normativity. I completed my high school education at Choate Rosemary Hall, where I graduated cum laude and was editor-in-chief of the school newspaper.',
    'Most of what I am currently interested in sits at the intersection of physics, philosophy, and economics.',
]

# last paragraph of the bio
MINNE = ('I also run MINNÉ Fragrances, a niche fragrance brand I built myself from the ground up. It started as a passion project to explore my artistic side, '
         'but is now somewhat of a full business. You can find it at <a href="https://www.minnefragrances.com">minnefragrances.com</a> '
         'and <a href="https://www.instagram.com/minne_fragrances">Instagram</a>.')

POSITIONS = [
    ('Stealth startup', 'Senior Advisor', 'Aug 2026 – Present'),
    ('DC Advisory', 'Investment Banking Analyst, Global Infrastructure', 'Aug 2024 – Aug 2026'),
    ('Copenhagen Infrastructure Partners', 'Summer Analyst', 'Jun 2023 – Aug 2023'),
    ('Milbank LLP', 'Summer Legal Analyst', 'Aug 2022 – Sep 2022'),
    ('RBC Capital Markets', 'Summer Analyst', 'Jun 2022 – Aug 2022'),
    ('Meatable', 'Research Intern', 'Mar 2021 – Jun 2022'),
    ('Christie’s', 'Research Intern', 'Jan 2020 – May 2020'),
    ('Council on Foreign Relations', 'Global Business Intern', 'Sep 2019 – Dec 2019'),
]

EDUCATION = [
    ('Columbia University', 'M.S. in Financial Engineering', 'Expected Dec 2027'),
    ('University of Chicago', 'B.A. in Economics (special honors)<br>B.A. in Philosophy (special honors)<br>Minor in theoretical physics', 'Jun 2024'),
    ('Choate Rosemary Hall', 'Diploma, cum laude', 'May 2019'),
]

HONORS = [
    ('2026', 'Infra Global ESG Awards', 'deal recognition',
     'Naturion’s inaugural financing was named ESG Nature Finance Deal of the Year and ESG Agribusiness Deal of the Year. The awards went to DC Advisory as Naturion’s exclusive financial adviser. I worked on the financing as the lead analyst and designed and ran the pricing study presented to lenders. <a href="https://www.dcadvisory.com/news-deals-insights/dc-advisory-in-the-press/dc-advisory-wins-esg-agribusiness-deal-of-the-year-and-esg-nature-finance-deal-of-the-year-at-the-infra-global-esg-awards-2026/">DC Advisory’s announcement</a>.'),
    ('2024', 'David S. Hu Award in Economics', 'University of Chicago',
     'Given for excellence in economics coursework and creativity in the senior thesis. Awarded for <i>Green Trade</i>. <a href="https://socialsciences.uchicago.edu/node/32896">Department announcement</a>.'),
    ('2024', 'Manley Thompson Book Prize', 'Department of Philosophy, University of Chicago',
     'Awarded for the senior thesis, <i>Beyond Scientific Validity</i>.'),
    ('2024', 'First student to win the thesis prizes in both economics and philosophy', 'University of Chicago', ''),
    ('2024', 'Special honors in economics and in philosophy', 'University of Chicago', ''),
    ('2020–24', 'Odyssey Scholar', 'University of Chicago', ''),
]

SHOW_FIGURE = False     # Figure 1 (the three-field map) is switched off for now; set True to bring it back

# 'slug' set -> the entry links to writings/<slug>.html once that page exists.
# 'mix' is the field mix (physics, economics, philosophy) used only by Figure 1.
WORKS = [
    {'n': 1, 'group': 'published', 'slug': 'green-trade', 'mix': (0.0, 1.0, 0.0),
     'title': 'Green Trade: A Theoretical Framework for Pricing Renewable Energy Certificates',
     'desc': 'An equilibrium model of interstate trading in renewable energy certificates, tested on the PJM market.',
     'meta': 'Honors thesis in economics, University of Chicago, 2024',
     'page_meta': 'Honors thesis, Department of Economics, University of Chicago. May 2024. Advised by Esteban Rossi-Hansberg.'},
    {'n': 2, 'group': 'published', 'slug': 'beyond-scientific-validity', 'mix': (0.0, 0.0, 1.0),
     'title': 'Beyond Scientific Validity: Disclosures of Truth and the Possibility of Normativity in Art',
     'desc': 'An argument, through Nietzsche and Heidegger, that art can ground normative claims where propositional truth cannot.',
     'meta': 'Honors thesis in philosophy, University of Chicago, 2024',
     'page_meta': 'Senior thesis, Department of Philosophy, University of Chicago. April 2024. Advised by Robert B. Pippin.'},
    {'n': 3, 'group': 'published', 'slug': 'renewable-energy-tax-incentives', 'mix': (0.0, 1.0, 0.0),
     'title': 'Renewable Energy and Infrastructure Investment: The Effectiveness of a Tax Incentive on Growth',
     'desc': 'A panel-data study of whether tax incentives go with faster growth in renewable energy investment across U.S. states.',
     'meta': 'Paul Douglas Institute, University of Chicago, 2023. Project leader.',
     'page_meta': 'Research paper, The Paul Douglas Institute, University of Chicago. Presented May 4, 2023.'},
    {'n': 4, 'group': 'working', 'slug': None, 'mix': (0.45, 0.55, 0.0), 'progress': True,
     'title': 'Correlated Data-Center Siting and Nodal Electricity Prices',
     'desc': 'On data centers and electricity prices on the PJM grid.',
     'meta': 'Master’s thesis, Columbia University, advised by Jushan Bai. In progress.'},
    {'n': 5, 'group': 'working', 'slug': None, 'mix': (0.0, 0.70, 0.30), 'progress': True,
     'title': 'AI and In-Person Learning: Effects on Growth',
     'desc': 'On AI, how people learn at work, and long-run growth.',
     'meta': 'Working paper in economics. In progress.'},
    {'n': 6, 'group': 'working', 'slug': None, 'mix': (0.08, 0.27, 0.65), 'progress': True,
     'title': 'Nihilism, Superintelligence, and Civilization',
     'desc': 'An essay on AI and the question of meaning.',
     'meta': 'Working paper in philosophy. In progress.'},
    # blog: 'title' is the public title; 'subtitle' is the essay's original title, shown on its page
    {'n': 7, 'group': 'blog', 'slug': 'existential-kant', 'mix': (0.0, 0.0, 1.0),
     'title': 'Why Should Duty Move Us?',
     'subtitle': 'The Existential Kant: Making Sense of Pure Practical Reason',
     'desc': 'How an unconditional moral law can matter to a finite being, read through Kant’s accounts of moral feeling and the sublime.',
     'meta': 'March 2024',
     'page_meta': 'Essay for Robert Pippin’s seminar Kant on Moral Meaning, University of Chicago. March 2024.'},
    {'n': 8, 'group': 'blog', 'slug': 'everlasting-masquerade', 'mix': (0.0, 0.0, 1.0),
     'title': 'Nietzsche’s Masks',
     'subtitle': 'An Everlasting Masquerade: The Implications of Nietzschean Esotericism and Solitude',
     'desc': 'On masks, solitude and esoteric writing in Nietzsche’s <i>Beyond Good and Evil</i>.',
     'meta': 'May 2023',
     'page_meta': 'Essay for a seminar with Robert Pippin, University of Chicago. May 2023.'},
    {'n': 9, 'group': 'blog', 'slug': 'philosophical-schism', 'mix': (0.0, 0.0, 1.0),
     'title': 'Facing Death, Alone or Together',
     'subtitle': 'Philosophical Schism: Heidegger and Hegel’s Competing Visions of Full Authentic Existence in the Face of Death',
     'desc': 'A Hegelian objection to Heidegger’s account of authenticity in <i>Being and Time</i>, and the reply Heidegger could give.',
     'meta': 'March 2023',
     'page_meta': 'Essay for Robert Pippin’s seminar on Heidegger’s <i>Being and Time</i>, University of Chicago. March 2023.'},
    {'n': 10, 'group': 'blog', 'slug': 'power-in-film', 'mix': (0.0, 0.0, 1.0),
     'title': 'Can a Film Be Sublime?',
     'subtitle': 'Power in Film: How Kant’s Theory of Fine Art Allows Cinema to Exhibit Dynamical Sublimity',
     'desc': 'An argument from Kant’s theory of fine art that cinema can exhibit the dynamical sublime, the experience of overwhelming power.',
     'meta': 'June 2022',
     'page_meta': 'Essay for a course with Eliza Little, University of Chicago. June 2022.'},
    {'n': 11, 'group': 'blog', 'slug': 'balthazar', 'mix': (0.0, 0.0, 1.0),
     'title': 'Why a Donkey’s Death Is Beautiful',
     'subtitle': 'Choreographing the Cinematograph Instead of Actors: How Balthazar’s Death Scene Derives its Beauty and Significance',
     'desc': 'Why the final scene of Bresson’s <i>Au hasard Balthazar</i> reads as beautiful, argued from his own theory of film.',
     'meta': '2022',
     'page_meta': 'Essay, University of Chicago. 2022.'},
]
