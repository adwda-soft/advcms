function initAgentQuery() {

    document.getElementById("agent_query_btn").addEventListener('click', async () => {

        const queryTextarea = document.getElementById('agent_query'); 
        const responseTextarea = document.getElementById('agent_response');
        const queryLookupNumInput = document.getElementById('max_match_lookup');
        const searchInPostsCheckbox = document.getElementById('search_in_posts');

        if (!queryTextarea || !responseTextarea || !queryLookupNumInput) {
            console.error('Required elements not found');
            return;
        }

        let serchInPosts = 0;
        if (searchInPostsCheckbox) {
            serchInPosts = searchInPostsCheckbox.checked ? 1 : 0;
        }

        responseTextarea.value = '';
        
        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ target: 'agent', querytext: queryTextarea.value, searchinposts: serchInPosts, lookupnum: queryLookupNumInput.value })
            });

            const data = await response.json();
            const message = data.message || 'No message returned';
            responseTextarea.value = message;
        } 
        catch (error) {
            responseTextarea.value = 'Error fetching POST data: ' + error.message;
        }
    }
    );
}
