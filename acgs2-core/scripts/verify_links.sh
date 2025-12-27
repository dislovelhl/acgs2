#!/bin/bash
# ACGS-2 Documentation Link Verifier
# Constitutional Hash: cdd01ef066bc6cf2

ROOT_DIR=$(pwd)
echo "🔍 Starting documentation link verification from $ROOT_DIR..."
ERRORS=0

# Find all markdown files
find . -name "*.md" -not -path "*/.*" | while read -r md_file; do
    # Extract links in format [text](path)
    links=$(grep -oE "\[[^]]+\]\([^)]+\)" "$md_file")
    
    while read -r link; do
        # Extract the path from the link
        target=$(echo "$link" | sed -E 's/\[.+\]\((.+)\)/\1/' | cut -d'#' -f1)
        
        # Skip external links
        if [[ "$target" =~ ^http ]] || [[ "$target" == "" ]] || [[ "$target" =~ ^mailto: ]]; then
            continue
        fi
        
        # Handle file:/// paths
        if [[ "$target" =~ ^file:// ]]; then
            target_path=${target#file://}
            if [ ! -e "$target_path" ]; then
                echo "❌ Dead absolute link in $md_file: $target"
                ERRORS=$((ERRORS + 1))
            fi
            continue
        fi

        # Handle absolute paths from project root
        if [[ "$target" == /* ]]; then
            resolved_target="$ROOT_DIR$target"
        else
            # Resolve path relative to current md file
            dir_path=$(dirname "$md_file")
            resolved_target="$dir_path/$target"
        fi
        
        # Check if file exists
        if [ ! -e "$resolved_target" ] && [ ! -d "$resolved_target" ]; then
            echo "❌ Dead link in $md_file: $target (Resolved to: $resolved_target)"
            ERRORS=$((ERRORS + 1))
        fi
    done <<< "$links"
done

if [ $ERRORS -gt 0 ]; then
    echo "⚠️  Verification finished with $ERRORS dead links."
    exit 1
else
    echo "✅ All internal links verified successfully!"
    exit 0
fi
