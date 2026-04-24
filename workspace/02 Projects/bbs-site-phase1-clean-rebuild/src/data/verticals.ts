export type VerticalLandingPage = {
  slug: string;
  seoTitle: string;
  metaDescription: string;
  navLabel: string;
  hero: {
    eyebrow: string;
    headline: string;
    subheadline: string;
    bullets: string[];
    sideCard: { label: string; value: string }[];
  };
  signals: { eyebrow: string; title: string; items: { title: string; body: string }[] };
  solution: {
    eyebrow: string;
    title: string;
    paragraphs: string[];
    principles: string[];
  };
  process: {
    eyebrow: string;
    title: string;
    steps: { title: string; body: string }[];
  };
  included: {
    eyebrow: string;
    title: string;
    items: { title: string; body: string }[];
  };
  outcomes: {
    eyebrow: string;
    title: string;
    items: string[];
    closing: string;
  };
  roi: {
    eyebrow: string;
    title: string;
    inputs: string[];
    current: string[];
    improved: string[];
    closing: string;
  };
  cta: { eyebrow: string; title: string; body: string; buttonLabel: string };
};

export const medSpaLanding: VerticalLandingPage = {
  slug: 'med-spa',
  seoTitle: 'Med Spa Systems Review | Beacon Bridge Strategies',
  metaDescription:
    'Beacon Bridge Strategies helps med spas tighten follow-up, booking flow, reminders, and lead visibility with controlled operational systems.',
  navLabel: 'Med Spa',
  hero: {
    eyebrow: 'Med Spa Systems',
    headline: 'A tighter lead-to-booked-consult system for med spas',
    subheadline:
      'We help med spas respond faster, recover missed-call opportunities, improve booking flow, reduce front-desk overload, and turn more existing demand into booked consults and collected revenue.',
    bullets: [
      'Connect calls, forms, Instagram, and campaigns into one operating flow',
      'Reduce front-desk overload without over-automating patient communication',
      'Improve visibility into consult booking, reminders, follow-up, and revenue capture'
    ],
    sideCard: [
      { label: 'Best fit', value: 'Owner-led clinics with steady inquiries and inconsistent follow-up' },
      { label: 'Primary goal', value: 'More booked consults from existing demand' },
      { label: 'Approach', value: 'Structured systems with reminders, guardrails, and reporting' }
    ]
  },
  signals: {
    eyebrow: 'Where med spas leak revenue',
    title: 'Leads are coming in. Booked consults are still slipping through.',
    items: [
      {
        title: 'Front desk overload',
        body: 'Patients, phones, forms, reschedules, and follow-up all compete for attention at the same time, so good leads wait too long for the next step.'
      },
      {
        title: 'Slow response to inbound demand',
        body: 'Website, ad, Instagram, and phone leads wait too long, so intent cools off before a consult is booked.'
      },
      {
        title: 'Weak visibility',
        body: 'Owners cannot easily see where leads are dropping off, which reminders went out, what still needs action, or where revenue is being left on the table.'
      }
    ]
  },
  solution: {
    eyebrow: 'What we build',
    title: 'Booking and follow-up infrastructure behind the demand you already have',
    paragraphs: [
      'This is not another marketing retainer. It is the operating system behind inquiry, response, booking, reminders, and reactivation.',
      'We help med spas capture every inquiry, route it into one pipeline, respond faster, support staff with cleaner workflows, and make consult booking easier to manage so more demand actually turns into revenue.',
      'Most clinics do not need more software. They need their current tools to work together with better structure.'
    ],
    principles: [
      'Approval steps before messages go out where needed',
      'Human-in-the-loop for patient-sensitive moments',
      'Clear staff permissions and role boundaries',
      'Fallbacks if automation fails',
      'Logging and visibility into response, reminders, and booking status'
    ]
  },
  process: {
    eyebrow: 'How this works',
    title: 'A controlled build, not a generic template drop',
    steps: [
      {
        title: 'Map lead flow',
        body: 'We review how calls, forms, Instagram messages, ads, and referrals currently enter the clinic.'
      },
      {
        title: 'Clean up routing',
        body: 'We make sure inquiries land in one system with clear ownership, stages, and next actions.'
      },
      {
        title: 'Install follow-up logic',
        body: 'Missed-call recovery, instant acknowledgment, booking workflows, reminders, and reactivation are set up around your actual process so more inquiries make it to consult.'
      },
      {
        title: 'Add visibility and controls',
        body: 'Dashboards, status tracking, approvals, and exception handling make the system easier to trust, manage, and improve.'
      },
      {
        title: 'Refine after launch',
        body: 'We tighten weak spots based on how the clinic actually runs once the system is live.'
      }
    ]
  },
  included: {
    eyebrow: 'What is included',
    title: 'Core system components for a med spa deployment',
    items: [
      {
        title: 'Missed-call recovery',
        body: 'Immediate follow-up paths so phone opportunities are not lost during busy hours.'
      },
      {
        title: 'Fast lead acknowledgment',
        body: 'Website and campaign leads get timely responses instead of waiting in a form inbox.'
      },
      {
        title: 'Booking workflow',
        body: 'Leads move toward consult scheduling with clearer routing, reminders, and next-step logic so fewer opportunities stall after first contact and more consults actually get booked.'
      },
      {
        title: 'Reminder and reschedule flows',
        body: 'Reduce no-shows and make rescheduling easier with more consistent operational follow-up.'
      },
      {
        title: 'Lead reactivation',
        body: 'Older leads are worked back into the pipeline through structured outreach and follow-up timing so past demand still has a chance to produce revenue.'
      },
      {
        title: 'CRM cleanup and pipeline structure',
        body: 'Stage design, ownership rules, and cleaner tracking so the clinic is not operating from scattered tools.'
      },
      {
        title: 'Dashboard and reporting',
        body: 'Clear views into leads, booked consults, reminder activity, no-shows, follow-up performance, and revenue capture.'
      },
      {
        title: 'Workflow alignment with the team',
        body: 'The system is matched to how the clinic actually operates instead of forcing a generic workflow.'
      }
    ]
  },
  outcomes: {
    eyebrow: 'What improves',
    title: 'What a stronger system should change',
    items: [
      'Faster response to new leads',
      'More recovered missed-call opportunities',
      'More booked consults from existing lead volume',
      'Less front-desk overload from repetitive follow-up',
      'More consistent reminders and fewer no-shows',
      'Better visibility into lead sources, booking performance, and revenue capture'
    ],
    closing:
      'The goal is straightforward: fewer missed leads, more booked consults, less front-desk strain, and a clinic that captures more revenue with more control.'
  },
  roi: {
    eyebrow: 'Simple ROI framing',
    title: 'A modest booking lift can justify the system quickly',
    inputs: ['120 leads per month', 'Current consult booking rate: 20%', 'Average value of a new booked treatment plan: $1,500'],
    current: ['120 leads × 20% booking rate = 24 booked consults', '24 booked consults × $1,500 = $36,000 in revenue'],
    improved: ['If stronger response and follow-up move booking rate from 20% to 28%:', '120 leads × 28% booking rate = 33.6 booked consults', 'That is about 10 more booked consults per month', '10 additional consults × $1,500 = $15,000 more monthly revenue', 'That is $180,000 per year from the same lead volume'],
    closing:
      'Even if the actual lift is smaller, the economics are still clear. Better follow-up on existing demand is often one of the highest-leverage fixes available.'
  },
  cta: {
    eyebrow: 'Next step',
    title: 'If consults are slipping between inquiry and follow-up, book a systems review.',
    body: 'We can show you where the booking process is breaking, what should be cleaned up first, and what a more reliable operating flow would look like.',
    buttonLabel: 'Book a Systems Review'
  }
};
