def get_my_profile_block(profile_info, parent_origin):

    user_email = profile_info.get('email') if profile_info else None # Extract user email
    profile_block = f"""
            **Answer to query like "who i am" ?**:
            You are {profile_info.get("name", "an unknown user")}, a {profile_info.get("role", "team member")} at {profile_info.get("company_name", "your organization")}
            with designation {profile_info.get("designation", "employee")}. 
            Use this information to personalize your answers. Respond accurately when asked about the user's identity.
            """
    
    return profile_block, user_email, parent_origin