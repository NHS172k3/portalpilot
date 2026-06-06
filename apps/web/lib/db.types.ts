export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export interface Database {
  public: {
    Tables: {
      agent_events: {
        Row: {
          id: number
          task_id: string
          type: string
          payload: Json
          timestamp: string
        }
        Insert: {
          id?: number
          task_id: string
          type: string
          payload?: Json
          timestamp?: string
        }
        Update: Partial<Database['public']['Tables']['agent_events']['Insert']>
      }
      attributes: {
        Row: {
          id: number
          business_profile_id: string
          key: string
          label: string
          value: string
          sensitivity: string
          notes: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          business_profile_id: string
          key: string
          label: string
          value: string
          sensitivity?: string
          notes?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['attributes']['Insert']>
      }
      business_profiles: {
        Row: {
          id: string
          name: string
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          name: string
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['business_profiles']['Insert']>
      }
      documents: {
        Row: {
          id: string
          business_profile_id: string
          filename: string
          mime: string
          blob_ref: string | null
          created_at: string
        }
        Insert: {
          id?: string
          business_profile_id: string
          filename: string
          mime: string
          blob_ref?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['documents']['Insert']>
      }
      extracted_facts: {
        Row: {
          id: string
          business_profile_id: string | null
          document_id: string | null
          source: string | null
          key: string
          value: string
          evidence_note: string | null
          confidence: number
          sensitivity: string
          expiry_marker: string | null
          created_at: string
        }
        Insert: {
          id?: string
          business_profile_id?: string | null
          document_id?: string | null
          source?: string | null
          key: string
          value: string
          evidence_note?: string | null
          confidence?: number
          sensitivity?: string
          expiry_marker?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['extracted_facts']['Insert']>
      }
      field_records: {
        Row: {
          id: string
          task_id: string
          field_key: string
          label: string
          section: string
          proposed_value: string | null
          sources: Json
          confidence: number
          sensitivity: string
          status: string
          reason: string
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          task_id: string
          field_key: string
          label: string
          section: string
          proposed_value?: string | null
          sources?: Json
          confidence?: number
          sensitivity?: string
          status: string
          reason?: string
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['field_records']['Insert']>
      }
      filing_tasks: {
        Row: {
          id: string
          business_profile_id: string
          form_definition_id: string | null
          status: string
          origin: string
          blocker: Json | null
          notes: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          business_profile_id: string
          form_definition_id?: string | null
          status?: string
          origin?: string
          blocker?: Json | null
          notes?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['filing_tasks']['Insert']>
      }
      form_definitions: {
        Row: {
          id: string
          jurisdiction: string
          agency: string
          name: string
          portal_url: string | null
          prerequisites: Json
          notes: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          jurisdiction: string
          agency: string
          name: string
          portal_url?: string | null
          prerequisites?: Json
          notes?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['form_definitions']['Insert']>
      }
      form_fields: {
        Row: {
          id: number
          form_definition_id: string
          key: string
          label: string
          section: string
          type: string
          options: Json | null
          sensitivity: string
          required: boolean
          human_only: boolean
          provenance: string
          conditional_on: string | null
          notes: string | null
          position: number | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          form_definition_id: string
          key: string
          label: string
          section: string
          type: string
          options?: Json | null
          sensitivity?: string
          required?: boolean
          human_only?: boolean
          provenance?: string
          conditional_on?: string | null
          notes?: string | null
          position?: number | null
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['form_fields']['Insert']>
      }
      recommendations: {
        Row: {
          id: string
          task_id: string
          reason: string
          prerequisites: Json
          fee: string | null
          timeline: string | null
          warnings: Json
          source_links: Json
          confidence: number
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          task_id: string
          reason?: string
          prerequisites?: Json
          fee?: string | null
          timeline?: string | null
          warnings?: Json
          source_links?: Json
          confidence?: number
          created_at?: string
          updated_at?: string
        }
        Update: Partial<Database['public']['Tables']['recommendations']['Insert']>
      }
    }
    Views: Record<string, never>
    Functions: Record<string, never>
    Enums: Record<string, never>
    CompositeTypes: Record<string, never>
  }
}
