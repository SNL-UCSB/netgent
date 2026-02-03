from phoenix import Client
import pandas as pd
from datetime import datetime
import os
import json

def main():
    try:
        client = Client()
        print("Connected to Phoenix.")
        
        print("Fetching spans...")
        # Fetch all spans as a dataframe
        df = client.get_spans_dataframe(project_name="netgent-default", limit=100000, timeout=None)
        
        print(f"Extracted {len(df)} spans.")
        
        # Filter for NetGent root spans to check status
        root_spans = df[df["name"] == "NetGent"]
        if not root_spans.empty:
            print("\n🔍 Root 'NetGent' Spans Status:")
            print(root_spans[["context.span_id", "status_code", "start_time", "end_time"]])
        else:
            print("\n❌ No 'NetGent' root spans found.")
            
        if not df.empty:
            # Check if columns exist
            required_cols = ['context.trace_id', 'context.span_id', 'name', 'status_code']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"Warning: Missing columns: {missing_cols}")
                # Try to map if possible or skip
            
            # Filter for successful spans if needed, but we wanted aggregation
            # Original query: status_code == 'OK'
            # We'll keep all spans for token counting but maybe filter for the main aggregation
            
            # Rename columns for easier access
            df = df.rename(columns={
                'context.trace_id': 'trace_id',
                'context.span_id': 'span_id',
                'attributes.llm.token_count.prompt': 'input_tokens',
                'attributes.llm.token_count.completion': 'output_tokens',
                'attributes.llm.token_count.total': 'total_tokens',
                'attributes.metadata': 'metadata'
            })
            
            # Ensure numeric columns are numeric (fill NaN with 0)
            token_cols = ['input_tokens', 'output_tokens', 'total_tokens']
            for col in token_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    df[col] = 0
            
            # --- Get Metadata from NetGent Spans ---
            print("Fetching metadata from NetGent root spans...")
            metadata_df = df[df['name'] == 'NetGent'][['trace_id', 'metadata']].copy()
            
            # --- Calculate Component Token Usage ---
            print("Calculating token usage by component...")
            
            # Helper to build parent map
            span_map = df.set_index('span_id')['name'].to_dict()
            parent_map = df.set_index('span_id')['parent_id'].to_dict()
            
            def find_ancestor(span_id, target_names, depth=15):
                current = span_id
                for _ in range(depth):
                    parent = parent_map.get(current)
                    if parent is None or pd.isna(parent):
                        return None
                    parent_name = span_map.get(parent)
                    if parent_name in target_names:
                        return parent_name
                    current = parent
                return None

            # Identify LLM spans
            llm_spans = df[df['name'] == 'ChatGoogleGenerativeAI'].copy()
            
            component_tokens = []
            for trace_id in df['trace_id'].unique():
                trace_llm = llm_spans[llm_spans['trace_id'] == trace_id]
                
                web_agent_input = 0
                web_agent_output = 0
                state_synthesis_input = 0
                state_synthesis_output = 0
                
                for _, row in trace_llm.iterrows():
                    ancestor = find_ancestor(row['span_id'], ['web_agent', 'state_synthesis'])
                    
                    input_t = row['input_tokens']
                    output_t = row['output_tokens']
                    
                    if ancestor == 'web_agent':
                        web_agent_input += input_t
                        web_agent_output += output_t
                    elif ancestor == 'state_synthesis':
                        state_synthesis_input += input_t
                        state_synthesis_output += output_t
                
                component_tokens.append({
                    'trace_id': trace_id,
                    'web_agent_input_tokens': web_agent_input,
                    'web_agent_output_tokens': web_agent_output,
                    'state_synthesis_input_tokens': state_synthesis_input,
                    'state_synthesis_output_tokens': state_synthesis_output,
                })
            
            component_df = pd.DataFrame(component_tokens)
            
            # --- Aggregation per Trace ---
            # Filter for successful spans for the main aggregation if desired, 
            # OR just aggregate everything by trace_id
            
            trace_agg = df.groupby('trace_id').agg({
                'start_time': 'min',
                'end_time': 'max',
                'input_tokens': 'sum',
                'output_tokens': 'sum', 
                'total_tokens': 'sum',
            })
            
            # Calculate duration
            # Convert to datetime if not already
            trace_agg['start_time'] = pd.to_datetime(trace_agg['start_time'])
            trace_agg['end_time'] = pd.to_datetime(trace_agg['end_time'])
            trace_agg['duration_seconds'] = (trace_agg['end_time'] - trace_agg['start_time']).dt.total_seconds()
            trace_agg = trace_agg.drop(columns=['start_time', 'end_time'])
            
            trace_agg = trace_agg.reset_index()
            
            # Merge Metadata
            if not metadata_df.empty:
                trace_agg = trace_agg.merge(metadata_df, on='trace_id', how='left')
            else:
                trace_agg['metadata'] = None
                
            # Merge Component Tokens
            if not component_df.empty:
                trace_agg = trace_agg.merge(component_df, on='trace_id', how='left')
            else:
                for col in ['web_agent_input_tokens', 'web_agent_output_tokens', 'state_synthesis_input_tokens', 'state_synthesis_output_tokens']:
                    trace_agg[col] = 0
            
            # Fill NaNs for tokens
            for col in ['web_agent_input_tokens', 'web_agent_output_tokens', 'web_agent_total_tokens', 
                        'state_synthesis_input_tokens', 'state_synthesis_output_tokens', 'state_synthesis_total_tokens']:
                if col not in trace_agg.columns:
                     trace_agg[col] = 0 # Initialize if missing
                else:
                     trace_agg[col] = trace_agg[col].fillna(0)

            # Calculate totals
            trace_agg['web_agent_total_tokens'] = trace_agg['web_agent_input_tokens'] + trace_agg['web_agent_output_tokens']
            trace_agg['state_synthesis_total_tokens'] = trace_agg['state_synthesis_input_tokens'] + trace_agg['state_synthesis_output_tokens']
            
            print(f"\n📊 Found {len(trace_agg)} unique traces.")
            # Stringify metadata for display
            display_df = trace_agg.copy()
            # Handle metadata column potentially being mixed types or objects
            # display_df['metadata'] = display_df['metadata'].apply(lambda x: str(x) if x is not None else '')
            
            cols_to_show = ['trace_id', 'duration_seconds', 'input_tokens', 'output_tokens', 'total_tokens', 
                            'web_agent_input_tokens', 'web_agent_output_tokens', 'web_agent_total_tokens',
                            'state_synthesis_input_tokens', 'state_synthesis_output_tokens', 'state_synthesis_total_tokens', 'metadata']
            
            # Ensure all cols exist
            cols_to_show = [c for c in cols_to_show if c in display_df.columns]
            print("\nTrace Summary:")
            print(display_df[cols_to_show].to_string())
            
            # Overall stats
            print("\n📊 Overall Token Usage:")
            print(f"   Total Input Tokens:  {int(trace_agg['input_tokens'].sum()):,}")
            print(f"   Total Output Tokens: {int(trace_agg['output_tokens'].sum()):,}")
            print(f"   Total Tokens:        {int(trace_agg['total_tokens'].sum()):,}")
            
            # Export
            output_dir = os.path.dirname(os.path.abspath(__file__))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"traces_export_{timestamp}.csv")
            
            # Prepare for CSV (stringify JSON/dicts)
            # metadata column should be stringified
            if 'metadata' in trace_agg.columns:
                trace_agg['metadata'] = trace_agg['metadata'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x) if x is not None else '')

            column_order = ['trace_id', 'duration_seconds', 'input_tokens', 'output_tokens', 'total_tokens',
                           'web_agent_input_tokens', 'web_agent_output_tokens', 'web_agent_total_tokens',
                           'state_synthesis_input_tokens', 'state_synthesis_output_tokens', 'state_synthesis_total_tokens', 'metadata']
            
            final_cols = [col for col in column_order if col in trace_agg.columns]
            trace_agg[final_cols].to_csv(output_file, index=False)
            print(f"\n✅ Exported {len(trace_agg)} traces to: {output_file}")
            
        else:
            print("No traces to export.")
            
    except Exception as e:
        print(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()