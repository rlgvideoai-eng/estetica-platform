export interface ServiceItem {
  name: string
  price: number
  duration: number
}

export interface ServiceCategory {
  id: string
  name: string
  icon: string
  description: string
  items: ServiceItem[]
}

export interface FAQItem {
  question: string
  answer: string
}

export interface BusinessInfo {
  name: string
  tagline: string
  description: string
  phone: string
  email: string
  address: string
  instagram: string
  mapsUrl: string
  hours: {
    weekdays: string
    saturday: string
    sunday: string
  }
}

export interface ContentData {
  business: BusinessInfo
  services: ServiceCategory[]
  faqs: FAQItem[]
  gallery: string[]
}